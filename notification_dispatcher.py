"""
IntruderLens - Notification Dispatcher
=======================================
Sends the owner an alert (WhatsApp and/or Email) after an intruder photo is saved.

Public API:
    send_alert(trigger_type, image_path)   -> starts a background thread, returns immediately
    classify_trigger(trigger_source)       -> maps a pipeline trigger string to a TRIGGER_* type
    test_alert(image_path=None)            -> blocking test send for the --test-alert CLI

Channels (each independently enabled in config.py):
    * WhatsApp — Twilio WhatsApp API (`pip install twilio`). The photo is uploaded to a
      temporary public URL first, because Twilio can only attach media it can download.
      If the upload fails, the text alert is still sent without the photo.
    * Email    — smtplib + email.mime (standard library), photo attached directly.

Credentials:
    config.py only holds placeholders. Real values can be supplied without touching
    config.py through either (later wins):
      1. a [notifications] section in intruder_lens.ini (git-ignored), keys = lower-case
         config names, e.g. `twilio_auth_token = ...`
      2. environment variables prefixed INTRUDERLENS_, e.g. INTRUDERLENS_SMTP_PASSWORD

Every failure is caught and logged; nothing here can crash the daemon.
"""

import configparser
import json
import logging
import mimetypes
import os
import smtplib
import threading
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    import config
except ImportError:
    from . import config

logger = logging.getLogger("IntruderLens")

# -----------------------------------------------------------------------------
# Trigger types & activity descriptions
# -----------------------------------------------------------------------------

TRIGGER_WRONG_PASSWORD = "wrong_password"
TRIGGER_LID_OPEN = "lid_open"
TRIGGER_GUARD_FACE = "guard_face"
TRIGGER_GUARD_KEYPRESS = "guard_keypress"
TRIGGER_GUARD_MOUSE = "guard_mouse"

ACTIVITY_DESCRIPTIONS = {
    TRIGGER_WRONG_PASSWORD: "3 consecutive wrong password attempts detected",
    TRIGGER_LID_OPEN: "Laptop lid opened or woken from sleep",
    TRIGGER_GUARD_FACE: "Unknown face detected while Guard Mode was active",
    TRIGGER_GUARD_KEYPRESS: "Keyboard activity detected while Guard Mode was active",
    TRIGGER_GUARD_MOUSE: "Mouse/touchpad activity detected while Guard Mode was active",
}

# Values in config.py that mean "not configured yet"
_PLACEHOLDER_MARKERS = ("YOUR_", "XXXX", "your_email@", "your_app_password", "owner_email@")

# Config keys that may be overridden from intruder_lens.ini / environment variables
_OVERRIDABLE_KEYS = (
    "NOTIFY_VIA_WHATSAPP", "NOTIFY_VIA_EMAIL",
    "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM", "OWNER_WHATSAPP_NUMBER",
    "WHATSAPP_IMAGE_HOST", "IMGBB_API_KEY",
    "SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "OWNER_EMAIL",
)
_BOOL_KEYS = {"NOTIFY_VIA_WHATSAPP", "NOTIFY_VIA_EMAIL"}
_INT_KEYS = {"SMTP_PORT"}
INI_SECTION = "notifications"
ENV_PREFIX = "INTRUDERLENS_"

_HTTP_TIMEOUT = 15  # seconds, for image upload + SMTP


def classify_trigger(trigger_source: str) -> str:
    """Maps the human-readable trigger_source used by the capture pipeline to a TRIGGER_* type."""
    s = (trigger_source or "").lower()
    if "guard" in s:
        if "keyboard" in s or "key" in s:
            return TRIGGER_GUARD_KEYPRESS
        if "mouse" in s or "touchpad" in s:
            return TRIGGER_GUARD_MOUSE
        return TRIGGER_GUARD_FACE
    if "password" in s:
        return TRIGGER_WRONG_PASSWORD
    return TRIGGER_LID_OPEN


def build_message(trigger_type: str, photo_attached: bool = True, when: datetime | None = None) -> str:
    """Builds the fixed-format alert text shared by WhatsApp and Email."""
    activity = ACTIVITY_DESCRIPTIONS.get(trigger_type, "Suspicious activity detected")
    when = when or datetime.now()
    timestamp = when.strftime("%d %b %Y, %I:%M %p")   # e.g. 20 Nov 2026, 09:41 PM
    device = os.environ.get("COMPUTERNAME", "Unknown device")
    photo_line = "[Photo attached]" if photo_attached else "[Photo saved on device]"
    return (
        "Intruder Lens Alert\n"
        "\n"
        f"Activity : {activity}\n"
        f"Time     : {timestamp}\n"
        f"Device   : {device}\n"
        "\n"
        f"{photo_line}\n"
        "Stay safe."
    )


# -----------------------------------------------------------------------------
# Settings (config.py + git-ignored overrides)
# -----------------------------------------------------------------------------

def _load_settings() -> dict:
    """Reads notification settings: config.py, then intruder_lens.ini, then environment."""
    settings = {key: getattr(config, key, None) for key in _OVERRIDABLE_KEYS}

    overrides = {}
    ini_path = getattr(config, "CONFIG_FILE", None)
    if ini_path and os.path.isfile(ini_path):
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(ini_path, encoding="utf-8")
            if parser.has_section(INI_SECTION):
                for key in _OVERRIDABLE_KEYS:
                    if key.lower() in parser[INI_SECTION]:
                        overrides[key] = parser[INI_SECTION][key.lower()]
        except Exception as ex:
            logger.warning(f"Could not read notification settings from {ini_path}: {ex}")

    for key in _OVERRIDABLE_KEYS:
        env_val = os.environ.get(ENV_PREFIX + key)
        if env_val is not None:
            overrides[key] = env_val

    for key, raw in overrides.items():
        try:
            if key in _BOOL_KEYS:
                settings[key] = str(raw).strip().lower() in ("1", "true", "yes", "on")
            elif key in _INT_KEYS:
                settings[key] = int(raw)
            else:
                settings[key] = str(raw).strip()
        except ValueError:
            logger.warning(f"Ignoring invalid notification setting {key}={raw!r}")
    return settings


def _is_placeholder(value) -> bool:
    if value is None or str(value).strip() == "":
        return True
    return any(marker in str(value) for marker in _PLACEHOLDER_MARKERS)


def _missing(settings: dict, keys: tuple) -> list:
    return [k for k in keys if _is_placeholder(settings.get(k))]


# -----------------------------------------------------------------------------
# WhatsApp (Twilio)
# -----------------------------------------------------------------------------

def _multipart_post(url: str, fields: dict, file_field: str, file_path: str) -> bytes:
    """Minimal multipart/form-data POST using only the standard library."""
    boundary = "----IntruderLens" + uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
    filename = os.path.basename(file_path)
    ctype = mimetypes.guess_type(filename)[0] or "image/jpeg"
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; "
             f"filename=\"{filename}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
    with open(file_path, "rb") as f:
        body += f.read()
    body += f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(url, data=bytes(body), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("User-Agent", "IntruderLens/1.0")
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
        return resp.read()


def _upload_image(image_path: str, settings: dict) -> str | None:
    """
    Uploads the photo to a temporary public URL so Twilio can attach it.
    Hosts:
      * "litterbox" (default) — litterbox.catbox.moe, no account needed, file auto-deletes after 1 hour
      * "imgbb"               — api.imgbb.com, needs IMGBB_API_KEY, auto-deletes after 1 hour
      * "none"                — never upload; WhatsApp alerts are text-only
    Returns the public URL, or None on failure.
    """
    host = (settings.get("WHATSAPP_IMAGE_HOST") or "litterbox").strip().lower()
    try:
        if host == "none":
            return None
        if host == "imgbb":
            api_key = settings.get("IMGBB_API_KEY")
            if _is_placeholder(api_key):
                logger.warning("WHATSAPP_IMAGE_HOST is 'imgbb' but IMGBB_API_KEY is not set. Sending text only.")
                return None
            query = urllib.parse.urlencode({"key": api_key, "expiration": 3600})
            raw = _multipart_post(f"https://api.imgbb.com/1/upload?{query}", {}, "image", image_path)
            url = json.loads(raw.decode("utf-8"))["data"]["url"]
        else:
            raw = _multipart_post("https://litterbox.catbox.moe/resources/internals/api.php",
                                  {"reqtype": "fileupload", "time": "1h"}, "fileToUpload", image_path)
            url = raw.decode("utf-8").strip()
        if not url.startswith("https://"):
            raise ValueError(f"unexpected response: {url[:120]}")
        return url
    except Exception as ex:
        logger.warning(f"Photo upload for WhatsApp failed ({host}): {ex}. Sending text only.")
        return None


def _send_whatsapp(trigger_type: str, image_path: str | None, settings: dict) -> bool:
    missing = _missing(settings, ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN",
                                  "TWILIO_WHATSAPP_FROM", "OWNER_WHATSAPP_NUMBER"))
    if missing:
        logger.warning(f"WhatsApp alerts enabled but not configured: {', '.join(missing)}")
        return False
    try:
        from twilio.rest import Client
    except ImportError:
        logger.error("WhatsApp alerts need the 'twilio' package (pip install twilio).")
        return False

    def _wa(number: str) -> str:
        number = number.strip()
        return number if number.startswith("whatsapp:") else f"whatsapp:{number}"

    media_url = _upload_image(image_path, settings) if image_path and os.path.isfile(image_path) else None
    body = build_message(trigger_type, photo_attached=media_url is not None)
    try:
        client = Client(settings["TWILIO_ACCOUNT_SID"], settings["TWILIO_AUTH_TOKEN"])
        kwargs = {"from_": _wa(settings["TWILIO_WHATSAPP_FROM"]),
                  "to": _wa(settings["OWNER_WHATSAPP_NUMBER"]),
                  "body": body}
        if media_url:
            kwargs["media_url"] = [media_url]
        message = client.messages.create(**kwargs)
        logger.info(f"WhatsApp alert sent (sid={message.sid}, photo={'yes' if media_url else 'no'}).")
        return True
    except Exception as ex:
        logger.error(f"Failed to send WhatsApp alert: {ex}")
        return False


# -----------------------------------------------------------------------------
# Email (SMTP + STARTTLS)
# -----------------------------------------------------------------------------

def _send_email(trigger_type: str, image_path: str | None, settings: dict) -> bool:
    missing = _missing(settings, ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "OWNER_EMAIL"))
    if missing:
        logger.warning(f"Email alerts enabled but not configured: {', '.join(missing)}")
        return False
    try:
        has_photo = bool(image_path and os.path.isfile(image_path))
        activity = ACTIVITY_DESCRIPTIONS.get(trigger_type, "Suspicious activity detected")

        msg = MIMEMultipart()
        msg["Subject"] = f"IntruderLens Alert — {activity}"
        msg["From"] = settings["SMTP_USERNAME"]
        msg["To"] = settings["OWNER_EMAIL"]
        msg.attach(MIMEText(build_message(trigger_type, photo_attached=has_photo), "plain", "utf-8"))

        if has_photo:
            # Pass the subtype explicitly rather than relying on content sniffing
            ctype = mimetypes.guess_type(image_path)[0] or "image/jpeg"
            with open(image_path, "rb") as f:
                part = MIMEImage(f.read(), _subtype=ctype.split("/", 1)[1])
            part.add_header("Content-Disposition", "attachment", filename=os.path.basename(image_path))
            msg.attach(part)

        with smtplib.SMTP(settings["SMTP_HOST"], int(settings.get("SMTP_PORT") or 587),
                          timeout=_HTTP_TIMEOUT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings["SMTP_USERNAME"], settings["SMTP_PASSWORD"])
            server.send_message(msg)

        logger.info(f"Email alert sent to {settings['OWNER_EMAIL']}.")
        return True
    except Exception as ex:
        logger.error(f"Failed to send Email alert: {ex}")
        return False


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def _dispatch(trigger_type: str, image_path: str | None) -> dict:
    """Sends to every enabled channel. Blocking. Returns {channel: success}."""
    results = {}
    try:
        settings = _load_settings()
        if not settings.get("NOTIFY_VIA_WHATSAPP") and not settings.get("NOTIFY_VIA_EMAIL"):
            logger.info("Notifications are off (silent mode) — photo saved to disk only.")
            return results
        if settings.get("NOTIFY_VIA_WHATSAPP"):
            results["whatsapp"] = _send_whatsapp(trigger_type, image_path, settings)
        if settings.get("NOTIFY_VIA_EMAIL"):
            results["email"] = _send_email(trigger_type, image_path, settings)
    except Exception as ex:   # last-resort guard: never let a notification error escape
        logger.error(f"Notification dispatcher error: {ex}")
    return results


def send_alert(trigger_type: str, image_path: str | None) -> None:
    """
    Non-blocking: dispatches the alert on a background thread and returns immediately.
    The thread is non-daemon so a one-shot CLI run (e.g. --test-lid) waits for delivery
    before exiting; network timeouts keep it bounded.
    """
    try:
        threading.Thread(target=_dispatch, args=(trigger_type, image_path),
                         name="NotificationDispatcher", daemon=False).start()
    except Exception as ex:
        logger.error(f"Could not start notification thread: {ex}")


def describe_channels() -> str:
    """Short status string for --status."""
    s = _load_settings()
    channels = [name for name, on in (("WhatsApp", s.get("NOTIFY_VIA_WHATSAPP")),
                                      ("Email", s.get("NOTIFY_VIA_EMAIL"))) if on]
    return " + ".join(channels) if channels else "Off (silent mode — photos saved to disk only)"


def test_alert(image_path: str | None = None) -> dict:
    """Blocking test send used by --test-alert. Returns {channel: success}."""
    return _dispatch(TRIGGER_LID_OPEN, image_path)
