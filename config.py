"""
IntruderLens - Configuration Module
Centralizes operational parameters, security thresholds, paths, and alert settings.
"""

import os
from pathlib import Path

# Project Base Directory
PROJECT_DIR = Path(__file__).resolve().parent

# Base Paths (default to user-accessible project directory, ensuring zero permission errors)
CAPTURES_DIR = PROJECT_DIR / "captures"
LOGS_DIR = PROJECT_DIR / "logs"
CONFIG_FILE = PROJECT_DIR / "intruder_lens.ini"
MODELS_DIR = PROJECT_DIR / "models"
WHITELIST_DIR = PROJECT_DIR / "trusted_faces"

# Fallback System Paths (ProgramData)
SYSTEM_PROGRAM_DATA = os.environ.get("ALLUSERSPROFILE", r"C:\ProgramData")
SYSTEM_APP_DIR = Path(SYSTEM_PROGRAM_DATA) / "IntruderLens"

# Security & Event Log Policy (Failed Password Attempts)
TARGET_EVENT_IDS = {
    4625: "LOGON_FAILED",
    4624: "LOGON_SUCCESS"
}

# Interactive Logon Types to monitor:
# 2  = Interactive (Console / Lock Screen)
# 7  = Unlock (Lock screen unlock attempt)
# 10 = RemoteInteractive (Terminal Services / RDP)
INTERACTIVE_LOGON_TYPES = {2, 7, 10}

# Threshold Configuration for Wrong Passwords
FAILED_ATTEMPT_THRESHOLD = 3        # Number of failed attempts required to trigger capture
ROLLING_WINDOW_SECONDS = 120        # Time window (seconds) to evaluate failed attempts
COOLDOWN_SECONDS = 30               # Minimum time between successive camera snaps
POLL_INTERVAL_SECONDS = 1.0         # Event log polling cycle time

# Lid-Open & Laptop Wake Detection Configuration
LID_OPEN_CAPTURE_ENABLED = True     # Capture snapshot when laptop lid is opened or woken
LID_COOLDOWN_SECONDS = 20           # Minimum cooldown between lid-open snaps (anti-bounce)
LID_HARDWARE_SETTLE_SECONDS = 0.8   # Delay to allow USB bus and camera sensor power to stabilize upon wake

# System Event Log IDs for Wake / Resume
# Kernel-Power 507: Modern Standby exit (contains LidOpenState)
# Kernel-Power 107: System resumed from sleep
# Power-Troubleshooter 1: System resumed from low power state
SYSTEM_WAKE_EVENT_IDS = {507, 107, 1}

# Face Recognition & Whitelisting Configuration
FACE_RECOGNITION_ENABLED = True     # Enable intelligent owner face recognition
FACE_MATCH_THRESHOLD = 0.35         # SFace cosine similarity threshold (0.32-0.363 recommended)
IGNORE_AUTHORIZED_FACES = True      # If True, suppress photo saving and warnings for recognized owner/family
SAVE_AUTHORIZED_SESSIONS = False    # If True, saves authorized logins silently under captures/authorized_*.jpg

YUNET_MODEL_PATH = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
SFACE_MODEL_PATH = MODELS_DIR / "face_recognition_sface_2021dec.onnx"

# Camera Capture Configuration
CAMERA_INDEX = 0                    # Default primary webcam index
WARMUP_FRAMES = 5                   # Frames to discard for auto-exposure/white balance stabilization
BURST_FRAMES_COUNT = 3              # Number of frames to evaluate for sharpness
JPEG_QUALITY = 95                   # High quality JPEG compression (0 - 100)

# Guard Mode (Manual Shortcut-Activated Watch Mode)
# Activate/deactivate with a global hotkey (2-3 simultaneous keys, e.g. "ctrl+shift+g")
# or, when GUARD_MODE_USE_PASSWORD is True, by typing a secret password anywhere.
# Values can also be changed from the CLI (--set-guard-shortcuts / --set-guard-password);
# CLI changes are persisted to intruder_lens.ini (git-ignored) and override the values below.
GUARD_MODE_ENABLED = True                   # Master switch: start the Guard Mode hotkey listener with the daemon
GUARD_MODE_ACTIVATE_SHORTCUT = "ctrl+shift+g"    # user-customizable
GUARD_MODE_DEACTIVATE_SHORTCUT = "ctrl+shift+s"  # user-customizable
GUARD_MODE_USE_PASSWORD = False             # True = use typed password instead of shortcut
GUARD_MODE_PASSWORD = ""                    # optional typed password (activates Guard Mode)
GUARD_MODE_DEACTIVATE_PASSWORD = ""         # optional separate deactivation password ("" = same as GUARD_MODE_PASSWORD)
GUARD_MODE_TRIGGER_ON_FACE = True           # capture if face detected
GUARD_MODE_TRIGGER_ON_KEYPRESS = True       # capture if key pressed
GUARD_MODE_TRIGGER_ON_MOUSE = True          # capture if mouse/touchpad activity

GUARD_MODE_ARM_DELAY_SECONDS = 5.0          # Grace period after activation so the owner can step away
GUARD_MODE_INPUT_GRACE_SECONDS = 2.0        # Delay before an input-triggered capture; cancelled if Guard Mode is deactivated meanwhile
GUARD_MODE_COOLDOWN_SECONDS = 10.0          # Minimum time between successive Guard Mode captures
GUARD_MODE_FACE_POLL_SECONDS = 1.0          # How often the webcam is scanned for a face while guarding
GUARD_MODE_MOUSE_MOVE_THRESHOLD_PX = 15     # Ignore mouse jitter smaller than this (pixels from armed position)

# =============================================================================
# Notifications (WhatsApp + Email) — see notification_dispatcher.py
# =============================================================================
# 🔴 Keep ONLY placeholder values in this file — it is committed to git.
# Put real credentials in a [notifications] section of intruder_lens.ini (git-ignored),
# using lower-case key names (e.g. twilio_auth_token = ...), or in environment variables
# prefixed INTRUDERLENS_ (e.g. INTRUDERLENS_SMTP_PASSWORD). Both override the values below.

# --- Notification Channels ---
# Both False = silent mode (photo is only saved to disk)
NOTIFY_VIA_WHATSAPP = False     # True to enable WhatsApp alerts
NOTIFY_VIA_EMAIL = False        # True to enable Email alerts

# --- WhatsApp (Twilio) ---
TWILIO_ACCOUNT_SID = "YOUR_TWILIO_SID_HERE"
TWILIO_AUTH_TOKEN = "YOUR_TWILIO_AUTH_TOKEN_HERE"
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"        # Twilio sandbox number
OWNER_WHATSAPP_NUMBER = "whatsapp:+91XXXXXXXXXX"      # owner's WhatsApp number

# Twilio can only attach a photo from a public URL, so the capture is uploaded to a
# temporary host first (it auto-deletes after 1 hour). If the upload fails, the text
# alert is still sent.
#   "litterbox" = litterbox.catbox.moe, no account needed (default)
#   "imgbb"     = api.imgbb.com, requires IMGBB_API_KEY
#   "none"      = never upload the photo; WhatsApp alerts are text-only
WHATSAPP_IMAGE_HOST = "litterbox"
IMGBB_API_KEY = "YOUR_IMGBB_API_KEY_HERE"

# --- Email (SMTP) ---
# Gmail:   smtp.gmail.com     port 587 (needs a Gmail App Password)
# Outlook: smtp.office365.com port 587
# Port 587 uses STARTTLS; port 465 uses implicit SSL (both supported)
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password_here"   # Gmail App Password, NOT main password
OWNER_EMAIL = "owner_email@gmail.com"
