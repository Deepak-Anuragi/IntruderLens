"""
IntruderLens - Guard Mode (Manual Shortcut-Activated Watch Mode)

The owner arms Guard Mode with a global hotkey (or a typed password) WITHOUT
locking the screen. While armed, any of the following triggers a silent webcam
capture which is then passed through the normal face-recognition / alert pipeline:

  * a human face appears in front of the webcam
  * any keyboard key is pressed
  * the mouse / touchpad is moved, clicked or scrolled

Threading model (nothing here blocks the main daemon loop):
  * `keyboard` / `mouse` library hooks run on their own listener threads and only
    flip flags / schedule a pending trigger (cheap, non-blocking).
  * A single "GuardModeWorker" thread owns the webcam while Guard Mode is active,
    scans for faces, and executes captures serially.

This module deliberately does not import intruder_lens; the capture and
face-recognition pipeline is injected via callables to avoid circular imports.
"""

from __future__ import annotations

import configparser
import logging
import math
import threading
import time
from collections import deque
from typing import Callable, Optional

try:
    import config
except ImportError:
    from . import config

logger = logging.getLogger("IntruderLens")

INI_SECTION = "guard_mode"

# Maps config attribute -> (ini key, type)
_PERSISTED_KEYS = {
    "GUARD_MODE_ACTIVATE_SHORTCUT": ("activate_shortcut", str),
    "GUARD_MODE_DEACTIVATE_SHORTCUT": ("deactivate_shortcut", str),
    "GUARD_MODE_USE_PASSWORD": ("use_password", bool),
    "GUARD_MODE_PASSWORD": ("password", str),
    "GUARD_MODE_DEACTIVATE_PASSWORD": ("deactivate_password", str),
}


# =============================================================================
# CONFIG HELPERS (validation + CLI persistence)
# =============================================================================

def validate_shortcut(shortcut: str) -> str:
    """
    Normalizes and validates a hotkey string such as "Ctrl + Shift + G".
    Requires 2 or 3 simultaneous keys. Raises ValueError if invalid.
    """
    if not shortcut or not shortcut.strip():
        raise ValueError("Shortcut cannot be empty.")

    parts = [p.strip().lower() for p in shortcut.split("+")]
    if any(not p for p in parts):
        raise ValueError(f"Malformed shortcut '{shortcut}'. Use the form 'ctrl+shift+g'.")
    if not 2 <= len(parts) <= 3:
        raise ValueError(f"Shortcut '{shortcut}' must combine 2 or 3 keys (got {len(parts)}).")
    if len(set(parts)) != len(parts):
        raise ValueError(f"Shortcut '{shortcut}' contains duplicate keys.")

    normalized = "+".join(parts)
    try:
        import keyboard
        keyboard.parse_hotkey(normalized)
    except ImportError:
        pass  # Cannot verify key names without the library; structure check is enough
    except ValueError as ex:
        raise ValueError(f"Unknown key in shortcut '{shortcut}': {ex}") from ex
    return normalized


def load_overrides() -> None:
    """Applies Guard Mode values saved via the CLI (intruder_lens.ini) on top of config.py."""
    ini_path = config.CONFIG_FILE
    if not ini_path.is_file():
        return

    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(ini_path, encoding="utf-8")
    except Exception as ex:
        logger.warning(f"Could not read {ini_path}: {ex}")
        return

    if not parser.has_section(INI_SECTION):
        return

    section = parser[INI_SECTION]
    for attr, (key, kind) in _PERSISTED_KEYS.items():
        if key not in section:
            continue
        try:
            value = section.getboolean(key) if kind is bool else section.get(key)
            setattr(config, attr, value)
        except ValueError as ex:
            logger.warning(f"Ignoring invalid '{key}' in {ini_path}: {ex}")


def save_overrides(**values) -> None:
    """
    Persists Guard Mode values to intruder_lens.ini (git-ignored) and applies them in-memory.
    Accepts config attribute names, e.g. save_overrides(GUARD_MODE_PASSWORD="secret").
    """
    ini_path = config.CONFIG_FILE
    parser = configparser.ConfigParser(interpolation=None)
    if ini_path.is_file():
        parser.read(ini_path, encoding="utf-8")
    if not parser.has_section(INI_SECTION):
        parser.add_section(INI_SECTION)

    for attr, value in values.items():
        if attr not in _PERSISTED_KEYS:
            raise KeyError(f"{attr} is not a persistable Guard Mode setting.")
        key, kind = _PERSISTED_KEYS[attr]
        parser.set(INI_SECTION, key, ("true" if value else "false") if kind is bool else str(value))
        setattr(config, attr, value)

    with open(ini_path, "w", encoding="utf-8") as f:
        parser.write(f)


def _deactivate_password() -> str:
    return config.GUARD_MODE_DEACTIVATE_PASSWORD or config.GUARD_MODE_PASSWORD


def describe_controls() -> str:
    """Human-readable summary of how Guard Mode is toggled (for logs / status output)."""
    if config.GUARD_MODE_USE_PASSWORD:
        separate = bool(config.GUARD_MODE_DEACTIVATE_PASSWORD)
        return "typed password (" + ("separate activate/deactivate passwords" if separate else "same password toggles") + ")"
    return f"activate '{config.GUARD_MODE_ACTIVATE_SHORTCUT}', deactivate '{config.GUARD_MODE_DEACTIVATE_SHORTCUT}'"


# =============================================================================
# GUARD MODE CONTROLLER
# =============================================================================

class GuardModeController:
    """
    :param process_frame:    callable(frame, trigger_source, details) -> None.
                             Runs face recognition, discards owner frames, saves + alerts otherwise.
    :param fallback_capture: callable() -> frame | None. Used when the webcam isn't already open.
    :param face_detector:    callable(frame) -> bool | None. True if a face is present;
                             None if the face engine is unavailable.
    """

    def __init__(self,
                 process_frame: Callable,
                 fallback_capture: Callable,
                 face_detector: Callable):
        self._process_frame = process_frame
        self._fallback_capture = fallback_capture
        self._face_detector = face_detector

        self._active = False
        self._armed_at = 0.0
        self._state_lock = threading.Lock()
        self._wake = threading.Event()
        self._stopped = threading.Event()

        self._pending: Optional[tuple] = None   # (deadline, trigger_source, details)
        self._last_capture = 0.0
        self._mouse_origin: Optional[tuple] = None

        self._cam = None
        self._cam_lock = threading.RLock()
        self._cam_retry_at = 0.0

        self._typed = deque(maxlen=max(len(config.GUARD_MODE_PASSWORD), len(_deactivate_password()), 1))

        self._keyboard = None
        self._mouse = None
        self._worker: Optional[threading.Thread] = None

    # ------------------------------------------------------------------ state

    @property
    def is_active(self) -> bool:
        return self._active

    def activate(self, source: str = "shortcut") -> None:
        with self._state_lock:
            if self._active:
                return
            self._active = True
            self._armed_at = time.time() + config.GUARD_MODE_ARM_DELAY_SECONDS
            self._pending = None
            self._mouse_origin = None
        logger.warning(
            f"🛡️ GUARD MODE ACTIVATED via {source}. Arming in {config.GUARD_MODE_ARM_DELAY_SECONDS:.0f}s "
            f"(face={config.GUARD_MODE_TRIGGER_ON_FACE}, keyboard={config.GUARD_MODE_TRIGGER_ON_KEYPRESS}, "
            f"mouse={config.GUARD_MODE_TRIGGER_ON_MOUSE})."
        )
        self._wake.set()

    def deactivate(self, source: str = "shortcut") -> None:
        with self._state_lock:
            if not self._active:
                return
            self._active = False
            cancelled = self._pending is not None
            self._pending = None
        logger.warning(f"🛡️ GUARD MODE DEACTIVATED via {source}." + (" Pending capture cancelled." if cancelled else ""))
        self._wake.set()

    def toggle(self, source: str = "shortcut") -> None:
        if self._active:
            self.deactivate(source)
        else:
            self.activate(source)

    def _is_armed(self) -> bool:
        return self._active and time.time() >= self._armed_at

    def _schedule_trigger(self, trigger_source: str, details: dict, delay: float) -> None:
        """Schedules a capture; keeps the earliest pending one so input floods don't postpone it."""
        with self._state_lock:
            if not self._is_armed() or self._pending is not None:
                return
            if time.time() - self._last_capture < config.GUARD_MODE_COOLDOWN_SECONDS:
                return
            self._pending = (time.time() + delay, trigger_source, details)
        self._wake.set()

    # ------------------------------------------------------------ lifecycle

    def start(self) -> bool:
        """Registers global hooks and starts the worker thread. Returns False if unavailable."""
        try:
            import keyboard
            self._keyboard = keyboard
        except ImportError:
            logger.error("Guard Mode requires the 'keyboard' package (pip install keyboard). Guard Mode disabled.")
            return False

        try:
            import mouse
            self._mouse = mouse
        except ImportError:
            self._mouse = None
            if config.GUARD_MODE_TRIGGER_ON_MOUSE:
                logger.warning("'mouse' package not installed (pip install mouse). Mouse/touchpad trigger disabled.")

        try:
            self._register_controls()
            self._keyboard.on_press(self._on_key_press)
            if self._mouse is not None and config.GUARD_MODE_TRIGGER_ON_MOUSE:
                self._mouse.hook(self._on_mouse_event)
        except Exception as ex:
            logger.error(f"Failed to register Guard Mode input hooks: {ex}")
            self.stop()
            return False

        self._worker = threading.Thread(target=self._worker_loop, daemon=True, name="GuardModeWorker")
        self._worker.start()
        logger.info(f"Guard Mode listener ready — {describe_controls()}.")
        return True

    def stop(self) -> None:
        self._stopped.set()
        self._active = False
        self._wake.set()
        try:
            if self._keyboard is not None:
                self._keyboard.unhook_all()
        except Exception:
            pass
        try:
            if self._mouse is not None:
                self._mouse.unhook_all()
        except Exception:
            pass
        if self._worker is not None and self._worker.is_alive():
            self._worker.join(timeout=3)
        self._release_camera()

    def _register_controls(self) -> None:
        if config.GUARD_MODE_USE_PASSWORD:
            if not config.GUARD_MODE_PASSWORD:
                raise ValueError("GUARD_MODE_USE_PASSWORD is True but GUARD_MODE_PASSWORD is empty.")
            return  # Passwords are matched inside _on_key_press

        activate = validate_shortcut(config.GUARD_MODE_ACTIVATE_SHORTCUT)
        deactivate = validate_shortcut(config.GUARD_MODE_DEACTIVATE_SHORTCUT)
        if activate == deactivate:
            self._keyboard.add_hotkey(activate, lambda: self.toggle(f"shortcut '{activate}'"))
        else:
            self._keyboard.add_hotkey(activate, lambda: self.activate(f"shortcut '{activate}'"))
            self._keyboard.add_hotkey(deactivate, lambda: self.deactivate(f"shortcut '{deactivate}'"))

    # ---------------------------------------------------------- input hooks
    # These run on the keyboard/mouse library threads: keep them fast.

    def _on_key_press(self, event) -> None:
        if config.GUARD_MODE_USE_PASSWORD and self._match_password(event.name):
            return  # The password keystroke toggled Guard Mode; never treat it as an intrusion

        if config.GUARD_MODE_TRIGGER_ON_KEYPRESS and self._is_armed():
            self._schedule_trigger(
                "Guard Mode: Keyboard Activity",
                {"input_event": f"key '{event.name}'"},
                delay=config.GUARD_MODE_INPUT_GRACE_SECONDS,
            )

    def _match_password(self, key_name: Optional[str]) -> bool:
        if not key_name:
            return False
        if key_name == "backspace":
            if self._typed:
                self._typed.pop()
            return False
        if key_name == "space":
            key_name = " "
        if len(key_name) != 1:
            return False  # Modifier / function keys are not part of the password

        self._typed.append(key_name)
        typed = "".join(self._typed)

        if self._active:
            target = _deactivate_password()
            if target and typed.endswith(target):
                self._typed.clear()
                self.deactivate("typed password")
                return True
        else:
            if typed.endswith(config.GUARD_MODE_PASSWORD):
                self._typed.clear()
                self.activate("typed password")
                return True
        return False

    def _on_mouse_event(self, event) -> None:
        if not self._is_armed():
            return
        mouse = self._mouse

        if isinstance(event, mouse.MoveEvent):
            if self._mouse_origin is None:
                self._mouse_origin = (event.x, event.y)
                return
            dx, dy = event.x - self._mouse_origin[0], event.y - self._mouse_origin[1]
            if math.hypot(dx, dy) < config.GUARD_MODE_MOUSE_MOVE_THRESHOLD_PX:
                return
            detail = "mouse/touchpad moved"
        elif isinstance(event, mouse.ButtonEvent):
            detail = f"mouse/touchpad {event.button} {event.event_type}"
        elif isinstance(event, mouse.WheelEvent):
            detail = "mouse/touchpad scroll"
        else:
            return

        self._schedule_trigger(
            "Guard Mode: Mouse/Touchpad Activity",
            {"input_event": detail},
            delay=config.GUARD_MODE_INPUT_GRACE_SECONDS,
        )

    # --------------------------------------------------------------- camera

    def _open_camera(self) -> bool:
        with self._cam_lock:
            if self._cam is not None:
                return True
            if time.time() < self._cam_retry_at:
                return False
            try:
                import cv2
                cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(config.CAMERA_INDEX)
                if not cap.isOpened():
                    raise RuntimeError(f"webcam index {config.CAMERA_INDEX} unavailable")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                for _ in range(config.WARMUP_FRAMES):
                    cap.read()
                self._cam = cap
                return True
            except Exception as ex:
                logger.warning(f"Guard Mode could not open webcam for face watch ({ex}). Retrying in 10s.")
                self._cam_retry_at = time.time() + 10
                return False

    def _release_camera(self) -> None:
        with self._cam_lock:
            if self._cam is not None:
                try:
                    self._cam.release()
                except Exception:
                    pass
                self._cam = None

    def borrow_best_frame(self):
        """
        Returns the sharpest frame from the already-open Guard Mode webcam, or None if the
        camera isn't held. Lets other triggers (lid-open, wrong password) capture while
        Guard Mode owns the device instead of failing to open it a second time.
        """
        with self._cam_lock:
            if self._cam is None:
                return None
            try:
                import cv2
            except ImportError:
                return None
            best, best_score = None, -1.0
            for _ in range(config.BURST_FRAMES_COUNT):
                ret, frame = self._cam.read()
                if not ret or frame is None:
                    continue
                score = cv2.Laplacian(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
                if score > best_score:
                    best, best_score = frame, score
                time.sleep(0.06)
            return best

    def _read_frame(self):
        with self._cam_lock:
            if self._cam is None:
                return None
            ret, frame = self._cam.read()
            return frame if ret else None

    # --------------------------------------------------------------- worker

    def _worker_loop(self) -> None:
        next_face_poll = 0.0
        face_engine_warned = False

        while not self._stopped.is_set():
            if not self._active:
                self._release_camera()
                self._wake.wait(timeout=1.0)
                self._wake.clear()
                continue

            now = time.time()
            watch_faces = config.GUARD_MODE_TRIGGER_ON_FACE

            # Open the webcam during the arm delay so it is warm by the time we're armed
            if watch_faces:
                self._open_camera()

            if not self._is_armed():
                self._wake.wait(timeout=0.2)
                self._wake.clear()
                continue

            # 1. Face presence scan
            if watch_faces and now >= next_face_poll:
                next_face_poll = now + config.GUARD_MODE_FACE_POLL_SECONDS
                frame = self._read_frame()
                if frame is not None:
                    has_face = self._detect_face(frame)
                    if has_face is None and not face_engine_warned:
                        logger.warning("Guard Mode face trigger unavailable: face engine offline (models missing).")
                        face_engine_warned = True
                    elif has_face:
                        self._schedule_trigger("Guard Mode: Face Detected", {"input_event": "face in front of webcam"}, delay=0.0)
            elif watch_faces:
                # Drain the driver buffer so the next frame is current, not seconds old
                with self._cam_lock:
                    if self._cam is not None:
                        self._cam.grab()

            # 2. Execute a due capture
            due = None
            with self._state_lock:
                if self._pending is not None and time.time() >= self._pending[0] and self._active:
                    due = self._pending
                    self._pending = None
                    self._last_capture = time.time()

            if due is not None:
                self._execute_capture(due[1], due[2])

            self._wake.wait(timeout=0.1)
            self._wake.clear()

        self._release_camera()

    def _detect_face(self, frame) -> Optional[bool]:
        try:
            import cv2
            h, w = frame.shape[:2]
            if w > 640:  # Downscale: presence detection doesn't need full resolution
                scale = 640.0 / w
                frame = cv2.resize(frame, (640, int(h * scale)))
            return self._face_detector(frame)
        except Exception as ex:
            logger.debug(f"Guard Mode face scan failed: {ex}")
            return False

    def _execute_capture(self, trigger_source: str, details: dict) -> None:
        frame = self.borrow_best_frame()
        if frame is None:
            frame = self._fallback_capture()
        if frame is None:
            logger.error(f"{trigger_source}: webcam returned no frame. Capture skipped.")
            return

        info = dict(details)
        info["guard_mode"] = "active"
        try:
            self._process_frame(frame, trigger_source, info)
        except Exception as ex:
            logger.exception(f"Guard Mode capture processing failed: {ex}")
