#!/usr/bin/env python3
"""
=============================================================================
IntruderLens — Stealth Windows Physical Security Daemon & Intruder Snapper
=============================================================================
Features:
1. Wrong Password Detection:
   Monitors Windows Security Event Log (Event ID 4625). Tracks failed attempts
   within a rolling time window (default: 3 attempts in 120s). Snaps intruder photo
   upon breach and auto-resets on successful logon (Event ID 4624).

2. Laptop Lid-Open & Wake-Up Detection:
   Monitors Windows System Event Log for Kernel-Power (Event ID 507/107) and
   Power-Troubleshooter (Event ID 1), as well as real-time Win32 power setting
   notifications (GUID_LIDSWITCH_STATE_CHANGE). Silently snaps a photo whenever
   the laptop lid is physically opened or the system wakes from sleep.

3. Face Recognition & Authorized Whitelist Subsystem:
   Evaluates captured faces against enrolled owner and family profiles using
   offline OpenCV YuNet (Face Detection) + SFace (Face Recognition). If the face
   belongs to the owner/whitelisted user, photo alerts are suppressed. If unknown,
   saves intruder evidence and dispatches instant warnings.

4. Multi-Channel Alerts:
   Optional instant dispatch via Telegram Bot API and TLS SMTP Email.

Target OS: Windows 10 / Windows 11
=============================================================================
"""

import os
import sys
import time
import logging
import ctypes
from ctypes import wintypes
import subprocess
import signal
import collections
import threading
import argparse
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Dynamic Dependency & DLL Resolver for Windows Services / LocalSystem
# ---------------------------------------------------------------------------
for user_site in Path("C:/Users").glob("*/AppData/Roaming/Python/Python*/site-packages"):
    if user_site.is_dir():
        site_str = str(user_site)
        if site_str not in sys.path:
            sys.path.insert(0, site_str)
        for sub in ("win32", "win32/lib", "pythonwin"):
            sub_path = str(user_site / sub)
            if sub_path not in sys.path:
                sys.path.insert(0, sub_path)
        dll_dir = user_site / "pywin32_system32"
        if dll_dir.is_dir() and hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(dll_dir))
            except Exception:
                pass

# Configuration & Subsystem imports
try:
    import config
except ImportError:
    from . import config

try:
    from face_engine import FaceRecognitionEngine
except ImportError:
    from .face_engine import FaceRecognitionEngine

# Standard library notification imports
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import urllib.request
import urllib.parse

# Global flag for graceful termination
RUNNING = True
FACE_ENGINE: FaceRecognitionEngine = None


# =============================================================================
# LOGGING SUBSYSTEM
# =============================================================================

def setup_logger() -> logging.Logger:
    """Configures multi-target logger with file and console outputs."""
    logger = logging.getLogger("IntruderLens")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(process)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File Handler
        try:
            config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
            log_file = config.LOGS_DIR / "intruder_lens.log"
            file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception:
            pass

        # Console / Stdout Handler
        try:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        except Exception:
            pass

    return logger


logger = setup_logger()


def ensure_directories():
    """Ensures captures, logs, models, and whitelist directories exist."""
    for directory in (config.CAPTURES_DIR, config.LOGS_DIR, config.MODELS_DIR, config.WHITELIST_DIR):
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except Exception as ex:
            logger.error(f"Failed to create directory {directory}: {ex}")


def get_face_engine() -> FaceRecognitionEngine:
    """Singleton getter for the Face Recognition Engine."""
    global FACE_ENGINE
    if FACE_ENGINE is None:
        FACE_ENGINE = FaceRecognitionEngine()
    return FACE_ENGINE


def is_admin() -> bool:
    """Checks whether the current process has Administrator privileges."""
    try:
        if bool(ctypes.windll.shell32.IsUserAnAdmin()):
            return True
    except Exception:
        pass

    try:
        import win32evtlog
        win32evtlog.EvtQuery("Security", win32evtlog.EvtQueryChannelPath, "*[System[(EventID=4624)]]")
        return True
    except Exception:
        return False


# =============================================================================
# SILENT HEADLESS WEBCAM CAPTURE SUBSYSTEM
# =============================================================================

class CameraCaptureModule:
    """
    Headless Webcam Capture Subsystem.
    Operates without GUI windows or taskbar pop-ups.
    Uses DirectShow (cv2.CAP_DSHOW), performs warmup frames for auto-exposure,
    burst captures frames, scores sharpness using Laplacian variance, and returns
    or persists the clearest frame.
    """

    @staticmethod
    def capture_best_frame(hardware_delay: float = 0.0):
        """
        Silently captures burst frames from webcam and returns the sharpest (best_frame, sharpness_score).
        Does not write to disk yet, enabling in-memory face recognition before deciding to save.
        """
        if hardware_delay > 0:
            logger.debug(f"Waiting {hardware_delay:.2f}s for camera hardware power stabilization...")
            time.sleep(hardware_delay)

        try:
            import cv2
        except ImportError:
            logger.critical("OpenCV ('opencv-python') is not installed. Webcam capture aborted.")
            return None, 0.0

        cap = None
        best_frame = None
        best_score = -1.0

        try:
            cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(config.CAMERA_INDEX)

            if not cap.isOpened():
                logger.error(f"Cannot access webcam at index {config.CAMERA_INDEX}. Camera may be detached or locked.")
                return None, 0.0

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

            # Warmup
            for _ in range(config.WARMUP_FRAMES):
                ret, _ = cap.read()
                if not ret:
                    time.sleep(0.05)

            # Burst
            for _ in range(config.BURST_FRAMES_COUNT):
                ret, frame = cap.read()
                if not ret or frame is None:
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                variance = cv2.Laplacian(gray, cv2.CV_64F).var()
                if variance > best_score:
                    best_score = variance
                    best_frame = frame
                time.sleep(0.06)

            return best_frame, best_score
        except Exception as e:
            logger.exception(f"Unexpected exception during camera frame capture: {e}")
            return None, 0.0
        finally:
            if cap is not None and cap.isOpened():
                cap.release()

    @staticmethod
    def save_frame_to_disk(frame, prefix: str = "intruder") -> str | None:
        """Saves a frame to the captures directory with high JPEG quality."""
        try:
            import cv2
            ensure_directories()
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp_str}.jpg"
            output_filepath = config.CAPTURES_DIR / filename

            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), config.JPEG_QUALITY]
            success = cv2.imwrite(str(output_filepath), frame, encode_params)

            if success:
                logger.info(f"📸 Snapshot saved to disk: {output_filepath}")
                return str(output_filepath)
            else:
                logger.error(f"OpenCV failed to write image file: {output_filepath}")
                return None
        except Exception as e:
            logger.error(f"Failed to save frame: {e}")
            return None

    @classmethod
    def capture_image(cls, prefix: str = "intruder", hardware_delay: float = 0.0) -> str | None:
        """Legacy helper: captures best frame and writes immediately to disk."""
        frame, _ = cls.capture_best_frame(hardware_delay=hardware_delay)
        if frame is None:
            return None
        return cls.save_frame_to_disk(frame, prefix=prefix)


# =============================================================================
# OPTIONAL NOTIFICATION SUBSYSTEM (Telegram / SMTP)
# =============================================================================

def send_telegram_alert(image_path: str, incident_title: str, incident_details: dict) -> bool:
    """Dispatches instant photo alert via Telegram Bot API."""
    if not config.TELEGRAM_ENABLED:
        return False

    token = config.TELEGRAM_BOT_TOKEN
    chat_id = config.TELEGRAM_CHAT_ID

    if token == "YOUR_BOT_TOKEN_HERE" or not chat_id:
        logger.warning("Telegram alert enabled but token/chat_id is not configured.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    caption_lines = [
        f"🚨 *{incident_title}*",
        f"• *Host:* `{os.environ.get('COMPUTERNAME', 'Localhost')}`",
        f"• *Timestamp:* `{incident_details.get('timestamp', datetime.now().isoformat())}`"
    ]
    for k, v in incident_details.items():
        if k != "timestamp":
            caption_lines.append(f"• *{k.replace('_', ' ').title()}:* `{v}`")

    caption = "\n".join(caption_lines)

    try:
        boundary = "----IntruderLensBoundary" + str(int(time.time()))
        body = bytearray()

        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'.encode())
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode())
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(b'Content-Disposition: form-data; name="parse_mode"\r\n\r\nMarkdown\r\n')

        filename = os.path.basename(image_path)
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="photo"; filename="{filename}"\r\n'.encode())
        body.extend(b"Content-Type: image/jpeg\r\n\r\n")

        with open(image_path, "rb") as f:
            body.extend(f.read())
        body.extend(f"\r\n--{boundary}--\r\n".encode())

        req = urllib.request.Request(url, data=bytes(body))
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                logger.info("Telegram alert dispatched successfully.")
                return True
            else:
                logger.error(f"Telegram API returned status: {response.status}")
                return False
    except Exception as ex:
        logger.error(f"Failed to dispatch Telegram alert: {ex}")
        return False


def send_email_alert(image_path: str, incident_title: str, incident_details: dict) -> bool:
    """Dispatches instant photo alert via TLS SMTP Email."""
    if not config.SMTP_ENABLED:
        return False

    if config.SMTP_USER == "your_email@gmail.com":
        logger.warning("SMTP alert enabled but user credentials not configured.")
        return False

    try:
        msg = MIMEMultipart()
        msg["Subject"] = f"🚨 SECURITY ALERT: {incident_title} on {os.environ.get('COMPUTERNAME', 'Localhost')}"
        msg["From"] = config.SMTP_USER
        msg["To"] = config.SMTP_RECIPIENT

        body_lines = [
            f"IntruderLens Security Event: {incident_title}",
            f"Host: {os.environ.get('COMPUTERNAME', 'Localhost')}",
            f"Timestamp: {incident_details.get('timestamp', datetime.now().isoformat())}",
            ""
        ]
        for k, v in incident_details.items():
            if k != "timestamp":
                body_lines.append(f"{k.replace('_', ' ').title()}: {v}")
        body_lines.append("\nAttached is the photo captured by the laptop webcam.")

        msg.attach(MIMEText("\n".join(body_lines), "plain"))

        with open(image_path, "rb") as img_file:
            img = MIMEImage(img_file.read(), name=os.path.basename(image_path))
            msg.attach(img)

        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email alert sent successfully to {config.SMTP_RECIPIENT}")
        return True
    except Exception as ex:
        logger.error(f"Failed to send SMTP email alert: {ex}")
        return False


# =============================================================================
# UNIFIED SECURITY INCIDENT PROCESSOR WITH FACE WHITELISTS
# =============================================================================

def process_security_trigger(trigger_source: str, details: dict, hardware_delay: float = 0.0):
    """
    Central handler for both Wrong Passwords and Lid-Open/Wake triggers.
    1. Captures webcam burst silently.
    2. Runs Face Recognition if enabled.
    3. If recognized as Owner/Family: Suppresses warning and skips intruder alert.
    4. If unknown or intruder: Saves photo and dispatches instant Telegram/Email alerts.
    """
    logger.warning("=" * 65)
    logger.warning(f"🚨 SECURITY TRIGGER ACTIVATED: {trigger_source}")
    logger.warning("Acquiring silent webcam frame for facial analysis...")
    logger.warning("=" * 65)

    frame, sharpness = CameraCaptureModule.capture_best_frame(hardware_delay=hardware_delay)
    if frame is None:
        logger.error("Webcam capture returned no valid frame. Camera may be busy or unavailable.")
        return

    # Face Recognition & Whitelist Matching
    is_whitelisted = False
    matched_name = None
    match_score = 0.0

    if config.FACE_RECOGNITION_ENABLED:
        engine = get_face_engine()
        if engine.is_ready:
            is_whitelisted, matched_name, match_score, _ = engine.identify_face(frame)
        else:
            logger.warning("Face recognition engine is not ready (models missing). Treating as unknown.")

    # Decision Matrix: Authorized Owner vs Unknown Intruder
    if is_whitelisted and matched_name:
        logger.info("=" * 65)
        logger.info(f"🟢 ACCESS GRANTED: Trusted Person Recognized: '{matched_name}' (Score: {match_score:.3f})")
        logger.info("Suppressing intruder alert — no warning will be dispatched.")
        logger.info("=" * 65)

        if config.SAVE_AUTHORIZED_SESSIONS:
            CameraCaptureModule.save_frame_to_disk(frame, prefix=f"authorized_{matched_name}")
        return

    # Unknown person / Intruder detected!
    logger.warning("=" * 65)
    logger.warning("🔴 UNAUTHORIZED / UNKNOWN PERSON IN FRONT OF LAPTOP!")
    logger.warning("Saving intruder evidence and dispatching alerts to owner...")
    logger.warning("=" * 65)

    prefix = "intruder" if "Password" in trigger_source else "lid_open"
    saved_path = CameraCaptureModule.save_frame_to_disk(frame, prefix=prefix)

    if saved_path and os.path.isfile(saved_path):
        incident_info = {
            "trigger_reason": trigger_source,
            "recognition_result": "Unknown / Unrecognized Person",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        incident_info.update(details)

        send_telegram_alert(saved_path, f"Unauthorized Physical Access ({trigger_source})", incident_info)
        send_email_alert(saved_path, f"Unauthorized Physical Access ({trigger_source})", incident_info)


# =============================================================================
# SECURITY EVENT LOG LISTENER (3x WRONG PASSWORDS)
# =============================================================================

class WindowsSecurityEventListener:
    """
    Monitors Windows Security Event Log (Security.evtx) via EvtQuery:
    - Event 4625: Logon Failure
    - Event 4624: Logon Success
    Tracks failures in a sliding window and triggers response upon reaching threshold.
    """

    def __init__(self):
        self.failed_attempts_queue = collections.deque()
        self.last_capture_timestamp = 0.0
        self.last_record_id = None
        self.xml_namespaces = {"ns": "http://schemas.microsoft.com/win/2004/08/events/event"}

    def initialize_watermark(self):
        """Sets watermark to latest existing record so only real-time new events are processed."""
        try:
            import win32evtlog
            h_query = win32evtlog.EvtQuery(
                "Security",
                win32evtlog.EvtQueryChannelPath | win32evtlog.EvtQueryReverseDirection,
                "*[System[(EventID=4625 or EventID=4624)]]"
            )
            events = win32evtlog.EvtNext(h_query, 1)
            if events:
                xml_content = win32evtlog.EvtRender(events[0], win32evtlog.EvtRenderEventXml)
                root = ET.fromstring(xml_content)
                rec_elem = root.find("./ns:System/ns:EventRecordID", self.xml_namespaces)
                if rec_elem is not None and rec_elem.text:
                    self.last_record_id = int(rec_elem.text)
                    logger.info(f"Security Log watermark initialized at RecordID: {self.last_record_id}")
            else:
                logger.info("Security log initialized. Listening from current head.")
        except Exception as e:
            logger.warning(f"Could not initialize Security watermark: {e}")

    def parse_event_xml(self, xml_content: str) -> dict | None:
        """Parses raw Windows Event XML into structured fields."""
        try:
            root = ET.fromstring(xml_content)
            system = root.find("./ns:System", self.xml_namespaces)
            if system is None:
                return None

            event_id_elem = system.find("./ns:EventID", self.xml_namespaces)
            record_id_elem = system.find("./ns:EventRecordID", self.xml_namespaces)
            time_elem = system.find("./ns:TimeCreated", self.xml_namespaces)

            event_id = int(event_id_elem.text) if event_id_elem is not None else 0
            record_id = int(record_id_elem.text) if record_id_elem is not None else 0
            event_time = time_elem.attrib.get("SystemTime", "") if time_elem is not None else ""

            event_data = {}
            for data in root.findall("./ns:EventData/ns:Data", self.xml_namespaces):
                name = data.attrib.get("Name")
                if name:
                    event_data[name] = data.text or ""

            logon_type = 0
            if "LogonType" in event_data and event_data["LogonType"].isdigit():
                logon_type = int(event_data["LogonType"])

            target_user = event_data.get("TargetUserName", "Unknown")
            workstation = event_data.get("WorkstationName", "Unknown")
            failure_status = event_data.get("Status", "")

            return {
                "event_id": event_id,
                "record_id": record_id,
                "timestamp": event_time,
                "logon_type": logon_type,
                "target_user": target_user,
                "workstation": workstation,
                "failure_status": failure_status
            }
        except Exception as ex:
            logger.debug(f"XML Parsing error for Security event: {ex}")
            return None

    def poll_events(self):
        """Queries new Security events since the last watermark."""
        try:
            import win32evtlog
        except ImportError:
            return

        query_xpath = "*[System[(EventID=4625 or EventID=4624)]]"
        try:
            h_query = win32evtlog.EvtQuery(
                "Security",
                win32evtlog.EvtQueryChannelPath,
                query_xpath
            )
        except Exception as e:
            logger.error(f"Failed to query Windows Security Event Log: {e}")
            return

        while RUNNING:
            try:
                events = win32evtlog.EvtNext(h_query, 20)
                if not events:
                    break

                for event in events:
                    xml_content = win32evtlog.EvtRender(event, win32evtlog.EvtRenderEventXml)
                    parsed = self.parse_event_xml(xml_content)
                    if not parsed:
                        continue

                    rec_id = parsed["record_id"]
                    if self.last_record_id is not None and rec_id <= self.last_record_id:
                        continue

                    self.last_record_id = rec_id
                    self.handle_event(parsed)
            except Exception:
                break

    def handle_event(self, event: dict):
        """Evaluates logon event against threshold and rolling window."""
        event_id = event["event_id"]
        logon_type = event["logon_type"]
        user = event["target_user"]
        now = time.time()

        # Event 4624: Successful Logon -> Reset state
        if event_id == 4624:
            if logon_type in config.INTERACTIVE_LOGON_TYPES:
                if len(self.failed_attempts_queue) > 0:
                    logger.info(
                        f"[LOGON SUCCESS] Authorized logon for user '{user}' (LogonType {logon_type}). "
                        f"Resetting failure counter from {len(self.failed_attempts_queue)} to 0."
                    )
                    self.failed_attempts_queue.clear()
            return

        # Event 4625: Failed Logon
        if event_id == 4625:
            if logon_type not in config.INTERACTIVE_LOGON_TYPES:
                logger.debug(f"Ignoring non-interactive logon failure (Type: {logon_type}, User: {user})")
                return

            self.failed_attempts_queue.append((now, event))
            logger.warning(
                f"[LOGON FAILED] Wrong password attempt for user '{user}' "
                f"(LogonType {logon_type}, Status: {event['failure_status']}). "
                f"Failures in window: {len(self.failed_attempts_queue)}/{config.FAILED_ATTEMPT_THRESHOLD}"
            )

            # Prune attempts outside rolling window
            cutoff = now - config.ROLLING_WINDOW_SECONDS
            while self.failed_attempts_queue and self.failed_attempts_queue[0][0] < cutoff:
                self.failed_attempts_queue.popleft()

            current_count = len(self.failed_attempts_queue)
            if current_count >= config.FAILED_ATTEMPT_THRESHOLD:
                if (now - self.last_capture_timestamp) >= config.COOLDOWN_SECONDS:
                    self.last_capture_timestamp = now
                    process_security_trigger(
                        trigger_source=f"3x Wrong Password Attempts ({config.FAILED_ATTEMPT_THRESHOLD} failures)",
                        details={
                            "target_account": event.get("target_user", "Unknown"),
                            "logon_type": event.get("logon_type", "Interactive")
                        }
                    )
                else:
                    logger.info(f"Threshold reached but cooldown active ({config.COOLDOWN_SECONDS}s). Skipping snapshot.")


# =============================================================================
# LAPTOP LID-OPEN & SYSTEM WAKE SUBSYSTEM
# =============================================================================

class LaptopLidAndWakeListener:
    """
    Detects when the laptop is opened or woke up from sleep:
    1. System Event Log Monitor:
       - Kernel-Power Event 507 (Modern Standby exit with LidOpenState: true)
       - Kernel-Power Event 107 (Resume from sleep)
       - Power-Troubleshooter Event 1 (Resume from low-power state)
    2. Real-Time Win32 Power Setting Notifications (GUID_LIDSWITCH_STATE_CHANGE).
    """

    def __init__(self):
        self.last_wake_record_id = None
        self.last_lid_capture_time = 0.0
        self.xml_namespaces = {"ns": "http://schemas.microsoft.com/win/2004/08/events/event"}

    def initialize_watermark(self):
        """Sets watermark to latest existing System log wake events."""
        try:
            import win32evtlog
            query = "*[System[Provider[@Name='Microsoft-Windows-Kernel-Power' or @Name='Microsoft-Windows-Power-Troubleshooter'] and (EventID=507 or EventID=107 or EventID=1)]]"
            h_query = win32evtlog.EvtQuery(
                "System",
                win32evtlog.EvtQueryChannelPath | win32evtlog.EvtQueryReverseDirection,
                query
            )
            events = win32evtlog.EvtNext(h_query, 1)
            if events:
                xml_content = win32evtlog.EvtRender(events[0], win32evtlog.EvtRenderEventXml)
                root = ET.fromstring(xml_content)
                rec_elem = root.find("./ns:System/ns:EventRecordID", self.xml_namespaces)
                if rec_elem is not None and rec_elem.text:
                    self.last_wake_record_id = int(rec_elem.text)
                    logger.info(f"System Wake watermark initialized at RecordID: {self.last_wake_record_id}")
            else:
                logger.info("System log initialized. Listening for wake/lid events.")
        except Exception as e:
            logger.warning(f"Could not initialize System wake watermark: {e}")

    def poll_system_log(self):
        """Polls Windows System log for Kernel-Power and Power-Troubleshooter wake events."""
        if not config.LID_OPEN_CAPTURE_ENABLED:
            return

        try:
            import win32evtlog
        except ImportError:
            return

        query = "*[System[Provider[@Name='Microsoft-Windows-Kernel-Power' or @Name='Microsoft-Windows-Power-Troubleshooter'] and (EventID=507 or EventID=107 or EventID=1)]]"
        try:
            h_query = win32evtlog.EvtQuery(
                "System",
                win32evtlog.EvtQueryChannelPath,
                query
            )
        except Exception as e:
            logger.error(f"Failed to query Windows System Event Log: {e}")
            return

        while RUNNING:
            try:
                events = win32evtlog.EvtNext(h_query, 10)
                if not events:
                    break

                for event in events:
                    xml_content = win32evtlog.EvtRender(event, win32evtlog.EvtRenderEventXml)
                    self.process_system_event_xml(xml_content)
            except Exception:
                break

    def process_system_event_xml(self, xml_content: str):
        """Parses and checks if a System event represents a lid open or wake event."""
        try:
            root = ET.fromstring(xml_content)
            system = root.find("./ns:System", self.xml_namespaces)
            if system is None:
                return

            event_id_elem = system.find("./ns:EventID", self.xml_namespaces)
            record_id_elem = system.find("./ns:EventRecordID", self.xml_namespaces)
            time_elem = system.find("./ns:TimeCreated", self.xml_namespaces)

            event_id = int(event_id_elem.text) if event_id_elem is not None else 0
            record_id = int(record_id_elem.text) if record_id_elem is not None else 0
            event_time = time_elem.attrib.get("SystemTime", "") if time_elem is not None else ""

            if self.last_wake_record_id is not None and record_id <= self.last_wake_record_id:
                return

            self.last_wake_record_id = record_id

            data_dict = {}
            for data in root.findall("./ns:EventData/ns:Data", self.xml_namespaces):
                name = data.attrib.get("Name")
                if name:
                    data_dict[name] = data.text or ""

            # Kernel-Power 507
            if event_id == 507:
                lid_state = data_dict.get("LidOpenState", "").lower()
                sleep_entered = data_dict.get("SleepEntered", "").lower()
                if lid_state == "true" or sleep_entered == "true":
                    logger.info(f"[KERNEL-POWER 507] Modern Standby exit (LidOpen: {lid_state}, SleepEntered: {sleep_entered}).")
                    self.trigger_lid_or_wake_capture(trigger_type="Lid Opened (Modern Standby Resume)", details={
                        "event_id": 507,
                        "lid_open_state": lid_state,
                        "timestamp": event_time
                    })
                    return

            # Kernel-Power 107
            elif event_id == 107:
                logger.info("[KERNEL-POWER 107] System resumed from sleep.")
                self.trigger_lid_or_wake_capture(trigger_type="Laptop Resumed from Sleep", details={
                    "event_id": 107,
                    "timestamp": event_time
                })
                return

            # Power-Troubleshooter 1
            elif event_id == 1:
                logger.info("[POWER-TROUBLESHOOTER 1] System returned from low power state.")
                self.trigger_lid_or_wake_capture(trigger_type="System Woke from Low Power State", details={
                    "event_id": 1,
                    "timestamp": event_time
                })
                return

        except Exception as ex:
            logger.debug(f"Error parsing system wake event: {ex}")

    def trigger_lid_or_wake_capture(self, trigger_type: str, details: dict):
        """Debounces and triggers capture & face verification when laptop lid opens."""
        now = time.time()
        if (now - self.last_lid_capture_time) < config.LID_COOLDOWN_SECONDS:
            logger.debug(f"Lid/wake event detected, but cooldown active ({config.LID_COOLDOWN_SECONDS}s). Skipping snapshot.")
            return

        self.last_lid_capture_time = now
        process_security_trigger(
            trigger_source=f"Laptop Opened ({trigger_type})",
            details=details,
            hardware_delay=config.LID_HARDWARE_SETTLE_SECONDS
        )


# =============================================================================
# REAL-TIME WIN32 POWER NOTIFICATION HOOK (LID SWITCH & DISPLAY ON)
# =============================================================================

def start_win32_power_notification_thread(lid_listener: LaptopLidAndWakeListener):
    """
    Registers a hidden Win32 message window for real-time power notifications:
    - GUID_LIDSWITCH_STATE_CHANGE: Triggered instantly when lid is physically opened.
    - GUID_CONSOLE_DISPLAY_STATE: Triggered when laptop screen powers on.
    """
    def message_loop():
        try:
            class GUID(ctypes.Structure):
                _fields_ = [
                    ('Data1', wintypes.DWORD),
                    ('Data2', wintypes.WORD),
                    ('Data3', wintypes.WORD),
                    ('Data4', wintypes.BYTE * 8)
                ]

            guid_lid = GUID(0xBA3E0F4D, 0xB817, 0x4094, (wintypes.BYTE * 8)(0xA2, 0xD1, 0xD5, 0x63, 0x79, 0xE6, 0xA0, 0xF3))
            guid_display = GUID(0x6FE69556, 0x704A, 0x47A0, (wintypes.BYTE * 8)(0x8F, 0x24, 0xC2, 0x8D, 0x93, 0x6F, 0xDA, 0x47))

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            WM_POWERBROADCAST = 0x0218
            PBT_POWERSETTINGCHANGE = 0x8013
            DEVICE_NOTIFY_WINDOW_HANDLE = 0x00000000

            WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

            class POWERBROADCAST_SETTING(ctypes.Structure):
                _fields_ = [
                    ('PowerSetting', GUID),
                    ('DataLength', wintypes.DWORD),
                    ('Data', wintypes.BYTE * 1)
                ]

            def wnd_proc(hwnd, msg, wparam, lparam):
                if msg == WM_POWERBROADCAST and wparam == PBT_POWERSETTINGCHANGE:
                    try:
                        p_setting = ctypes.cast(lparam, ctypes.POINTER(POWERBROADCAST_SETTING)).contents
                        setting_guid = p_setting.PowerSetting
                        if setting_guid.Data1 == guid_lid.Data1:
                            lid_state = p_setting.Data[0]
                            if lid_state == 1:
                                logger.info("[WIN32 POWER] Physical Lid Opened signal received!")
                                lid_listener.trigger_lid_or_wake_capture("Physical Laptop Lid Opened", {"source": "Win32_LidSwitch"})
                        elif setting_guid.Data1 == guid_display.Data1:
                            display_state = p_setting.Data[0]
                            if display_state == 1:
                                logger.info("[WIN32 POWER] Display powered on signal received.")
                                lid_listener.trigger_lid_or_wake_capture("Display Turned On", {"source": "Win32_DisplayState"})
                    except Exception as err:
                        logger.debug(f"Error handling power setting change: {err}")
                    return 1
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

            wndclass_proc = WNDPROC(wnd_proc)
            class WNDCLASS(ctypes.Structure):
                _fields_ = [
                    ('style', wintypes.UINT),
                    ('lpfnWndProc', WNDPROC),
                    ('cbClsExtra', ctypes.c_int),
                    ('cbWndExtra', ctypes.c_int),
                    ('hInstance', wintypes.HINSTANCE),
                    ('hIcon', wintypes.HICON),
                    ('hCursor', wintypes.HICON),
                    ('hbrBackground', wintypes.HBRUSH),
                    ('lpszMenuName', wintypes.LPCWSTR),
                    ('lpszClassName', wintypes.LPCWSTR)
                ]

            class_name = f"IntruderLens_PowerHook_{os.getpid()}"
            wc = WNDCLASS()
            wc.lpfnWndProc = wndclass_proc
            wc.hInstance = kernel32.GetModuleHandleW(None)
            wc.lpszClassName = class_name
            user32.RegisterClassW(ctypes.byref(wc))

            hwnd = user32.CreateWindowExW(
                0, class_name, "IntruderLensMsgWindow",
                0, 0, 0, 0, 0,
                0, 0, wc.hInstance, 0
            )

            if hwnd:
                user32.RegisterPowerSettingNotification(hwnd, ctypes.byref(guid_lid), DEVICE_NOTIFY_WINDOW_HANDLE)
                user32.RegisterPowerSettingNotification(hwnd, ctypes.byref(guid_display), DEVICE_NOTIFY_WINDOW_HANDLE)
                logger.info("Win32 Real-Time Lid-Switch & Display Power Notifications registered.")

                msg = wintypes.MSG()
                while RUNNING:
                    has_msg = user32.PeekMessageW(ctypes.byref(msg), hwnd, 0, 0, 1)
                    if has_msg:
                        user32.TranslateMessage(ctypes.byref(msg))
                        user32.DispatchMessageW(ctypes.byref(msg))
                    else:
                        time.sleep(0.1)
        except Exception as e:
            logger.debug(f"Win32 power notification hook stopped: {e}")

    th = threading.Thread(target=message_loop, daemon=True, name="Win32PowerHook")
    th.start()
    return th


# =============================================================================
# CLI UTILITIES & TEST COMMANDS
# =============================================================================

def test_camera():
    """Snaps an immediate test image and displays path and status."""
    print("=" * 60)
    print("IntruderLens: Testing Silent Headless Camera Capture...")
    print("=" * 60)
    img_path = CameraCaptureModule.capture_image(prefix="test_manual")
    if img_path and os.path.isfile(img_path):
        print(f"\n[SUCCESS] Photo successfully captured and saved to:\n  -> {img_path}\n")
    else:
        print("\n[FAILED] Camera capture failed. Ensure webcam is plugged in and not in use.\n")


def test_lid_simulation():
    """Simulates a laptop lid-open trigger."""
    print("=" * 60)
    print("IntruderLens: Simulating Laptop Lid-Open Event...")
    print("=" * 60)
    listener = LaptopLidAndWakeListener()
    listener.trigger_lid_or_wake_capture(
        trigger_type="Manual Lid-Open Test Simulation",
        details={"test_mode": True}
    )


def test_failed_logon_simulation():
    """Simulates 3 consecutive wrong password attempts."""
    print("=" * 60)
    print(f"IntruderLens: Simulating {config.FAILED_ATTEMPT_THRESHOLD} Wrong Password Attempts...")
    print("=" * 60)
    listener = WindowsSecurityEventListener()
    test_event = {
        "event_id": 4625,
        "record_id": 9999999,
        "timestamp": datetime.now().isoformat(),
        "logon_type": 2,
        "target_user": os.environ.get("USERNAME", "TestTargetUser"),
        "workstation": os.environ.get("COMPUTERNAME", "LocalWorkstation"),
        "failure_status": "0xC000006D"
    }
    for i in range(1, config.FAILED_ATTEMPT_THRESHOLD + 1):
        print(f" -> Injecting simulated failed password attempt {i}/{config.FAILED_ATTEMPT_THRESHOLD}...")
        listener.handle_event(test_event)
        time.sleep(0.5)


def check_system_status():
    """Displays comprehensive system diagnostics."""
    print("=" * 65)
    print("           IntruderLens System Diagnostics Report             ")
    print("=" * 65)

    has_admin = is_admin()
    print(f"[1] Administrative Privileges: {'YES (Can audit Security Log)' if has_admin else 'NO (Requires Elevation to read Security.evtx)'}")

    cam_ok = False
    try:
        import cv2
        cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, _ = cap.read()
            cam_ok = ret
            cap.release()
    except Exception:
        pass
    print(f"[2] Primary Webcam (Index {config.CAMERA_INDEX}): {'ONLINE & ACCESSIBLE' if cam_ok else 'OFFLINE OR LOCKED'}")

    ensure_directories()
    print(f"[3] Captures Directory: {config.CAPTURES_DIR} ({'EXISTS & WRITABLE' if config.CAPTURES_DIR.is_dir() else 'ERROR'})")
    print(f"[4] Logs Directory:     {config.LOGS_DIR} ({'EXISTS & WRITABLE' if config.LOGS_DIR.is_dir() else 'ERROR'})")

    engine = get_face_engine()
    print(f"[5] Face Recognition Engine: {'ONLINE (YuNet + SFace)' if engine.is_ready else 'OFFLINE (Missing ONNX models)'}")
    profiles = engine.list_enrolled_profiles()
    print(f"[6] Enrolled Trusted Profiles: {len(profiles)}")
    for name, count in profiles.items():
        print(f"      - {name} ({count} face samples)")

    existing_photos = list(config.CAPTURES_DIR.glob("*.jpg"))
    print(f"[7] Total Saved Snapshots: {len(existing_photos)}")
    if existing_photos:
        print("    Recent captures:")
        for p in sorted(existing_photos, key=lambda f: f.stat().st_mtime, reverse=True)[:5]:
            print(f"      - {p.name}")

    print("-" * 65)
    print(f"Wrong Password Threshold: {config.FAILED_ATTEMPT_THRESHOLD} attempts in {config.ROLLING_WINDOW_SECONDS}s")
    print(f"Lid-Open Capture Enabled: {config.LID_OPEN_CAPTURE_ENABLED} (Cooldown: {config.LID_COOLDOWN_SECONDS}s)")
    print(f"Ignore Authorized Faces:  {config.IGNORE_AUTHORIZED_FACES}")
    print(f"Telegram Notifications:   {config.TELEGRAM_ENABLED}")
    print(f"Email Notifications:      {config.SMTP_ENABLED}")
    print("=" * 65)


def setup_scheduled_task():
    """
    Registers a Windows Scheduled Task ('IntruderLensDaemon') to run IntruderLens
    silently in the user's interactive session with highest privileges.
    """
    python_exe = sys.executable
    script_path = str(Path(__file__).resolve())
    task_name = "IntruderLensDaemon"
    print(f"Creating Windows Scheduled Task: '{task_name}'...")

    cmd = [
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", f'"{python_exe}" "{script_path}" --run',
        "/sc", "onlogon",
        "/rl", "highest",
        "/f"
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[SUCCESS] Scheduled Task '{task_name}' successfully installed.")
            print("IntruderLens will now automatically start silently upon logon with full webcam and security auditing capabilities.")
        else:
            print(f"[FAILED] Failed to register task: {res.stderr.strip()}")
            print("Tip: Run this command from an elevated (Administrator) command prompt.")
    except Exception as ex:
        print(f"Error registering task: {ex}")


# =============================================================================
# DAEMON MAIN LOOP
# =============================================================================

def signal_handler(signum, frame):
    """Graceful termination handler."""
    global RUNNING
    logger.info(f"Termination signal received ({signum}). Shutting down IntruderLens...")
    RUNNING = False


def run_daemon():
    """Runs the main IntruderLens security daemon."""
    global RUNNING

    print(r"""
  ___       _                 _           _                      
 |_ _| _ _ | |_  _ _  _  _  __| | ___  _ _ | |   ___  _ _   ___  
  | | | ' \|  _|| '_|| || |/ _` |/ -_)| '_|| |__/ -_)| ' \ (_-<  
 |___||_||_| \__||_|   \_,_|\__,_|\___||_|  |____\___||_||_|/__/  
     Stealth Physical Security, Wake Sentry & Face Whitelisting
    """)

    logger.info("Initializing IntruderLens Daemon...")
    ensure_directories()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Preload face engine
    engine = get_face_engine()
    if engine.is_ready:
        profiles = engine.list_enrolled_profiles()
        logger.info(f"Face Recognition Engine active. Enrolled profiles: {list(profiles.keys())}")
    else:
        logger.warning("Face Recognition Engine offline. Captures will trigger for all wake/logon events.")

    # 1. Initialize Security Event Listener (Wrong Passwords)
    security_listener = WindowsSecurityEventListener()
    if is_admin():
        security_listener.initialize_watermark()
        logger.info(f"Security Log Monitoring active. Threshold: {config.FAILED_ATTEMPT_THRESHOLD} attempts / {config.ROLLING_WINDOW_SECONDS}s.")
    else:
        logger.warning(
            "Notice: Process is not running with Administrator privileges. "
            "Security Event Log auditing (Event 4625) may be restricted. "
            "Lid-Open and System Wake events will continue monitoring."
        )

    # 2. Initialize Lid-Open & Wake Listener
    lid_listener = LaptopLidAndWakeListener()
    if config.LID_OPEN_CAPTURE_ENABLED:
        lid_listener.initialize_watermark()
        start_win32_power_notification_thread(lid_listener)
        logger.info(f"Laptop Lid-Open & Wake Detection active. Cooldown: {config.LID_COOLDOWN_SECONDS}s.")

    logger.info("IntruderLens is actively guarding this machine. Press Ctrl+C to terminate.")

    try:
        while RUNNING:
            security_listener.poll_events()
            if config.LID_OPEN_CAPTURE_ENABLED:
                lid_listener.poll_system_log()
            time.sleep(config.POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received.")
    finally:
        logger.info("IntruderLens Daemon successfully stopped.")


def main():
    parser = argparse.ArgumentParser(description="IntruderLens - Stealth Physical Security & Intruder Snapper")
    parser.add_argument("--run", action="store_true", help="Start IntruderLens daemon in foreground")
    parser.add_argument("--test-camera", action="store_true", help="Capture a single test image from webcam")
    parser.add_argument("--test-lid", action="store_true", help="Simulate a laptop lid-open trigger")
    parser.add_argument("--test-failed-logon", action="store_true", help="Simulate reaching 3 wrong password attempts")
    parser.add_argument("--status", action="store_true", help="Display system status and diagnostics report")
    parser.add_argument("--setup-task", action="store_true", help="Install Windows Scheduled Task for auto-start")

    # Face Enrollment & Whitelist CLI commands
    parser.add_argument("--enroll-face", type=str, metavar="NAME", help="Enroll a trusted person via live webcam (e.g. --enroll-face Deepak)")
    parser.add_argument("--enroll-face-image", nargs=2, metavar=("NAME", "PATH"), help="Enroll a trusted person from photo on disk (e.g. --enroll-face-image Deepak C:/path/photo.jpg)")
    parser.add_argument("--list-faces", action="store_true", help="List all enrolled trusted faces in the whitelist")
    parser.add_argument("--remove-face", type=str, metavar="NAME", help="Remove an enrolled person from the whitelist")

    args = parser.parse_args()
    engine = get_face_engine()

    if args.enroll_face:
        engine.enroll_face_from_webcam(args.enroll_face)
    elif args.enroll_face_image:
        name, path = args.enroll_face_image
        engine.enroll_face_from_image(name, Path(path))
    elif args.list_faces:
        profiles = engine.list_enrolled_profiles()
        print("\n" + "=" * 50)
        print("          Trusted Enrolled Face Profiles          ")
        print("=" * 50)
        if not profiles:
            print("No trusted faces enrolled yet.")
            print("Enroll someone with: python intruder_lens.py --enroll-face 'Deepak'")
        else:
            for name, count in profiles.items():
                print(f" • {name}: {count} face reference samples")
        print("=" * 50 + "\n")
    elif args.remove_face:
        engine.remove_profile(args.remove_face)
    elif args.test_camera:
        test_camera()
    elif args.test_lid:
        test_lid_simulation()
    elif args.test_failed_logon:
        test_failed_logon_simulation()
    elif args.status:
        check_system_status()
    elif args.setup_task:
        setup_scheduled_task()
    else:
        run_daemon()


if __name__ == "__main__":
    main()
