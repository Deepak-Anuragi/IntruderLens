# IntruderLens — Stealth Windows Physical Security, Wake Sentry & Face Whitelisting

**IntruderLens** is an intelligent, automated, stealth physical security daemon designed for Windows 10/11 laptops and desktops. It continuously monitors security authentication events and hardware power states, silently verifying whoever is in front of the laptop using offline facial recognition.

---

## 🎯 Key Capabilities

1. **Intelligent Face Recognition & Whitelisting (New!)**:
   - Uses ultra-fast **OpenCV YuNet** (Face Detection) + **SFace** (Face Recognition ONNX).
   - **100% Offline & Local**: No external cloud APIs or privacy risks.
   - **Multi-Face Enrollment**: Enroll yourself (Owner) and family members.
   - **Smart Warning Suppression**: When you or family members open the laptop, your face matches the whitelist (`ACCESS GRANTED`) and alerts are suppressed.
   - **Intruder Detection**: When an unknown face or intruder is detected, saves photo evidence and immediately dispatches alerts to the owner.

2. **Laptop Lid-Open & Wake-Up Snap**:
   - Listens for Modern Standby exit (`Kernel-Power Event ID 507` with `LidOpenState: true`), sleep resume (`Kernel-Power Event ID 107` / `Power-Troubleshooter Event ID 1`).
   - Hooks into real-time Win32 power setting broadcasts (`GUID_LIDSWITCH_STATE_CHANGE` & `GUID_CONSOLE_DISPLAY_STATE`).
   - Built-in anti-bounce cooldown (default: 20s) prevents redundant captures when adjusting screen tilt.

3. **3x Wrong Password Snap**:
   - Continuously audits Windows Security Event Log (`Event ID 4625`).
   - Tracks failed attempts in a sliding time window (default: 3 attempts in 120s).
   - Auto-resets the failure queue upon successful logon (`Event ID 4624`).

4. **Multi-Channel Instant Alerts (Optional)**:
   - Built-in Telegram Bot API dispatcher with photo attachment.
   - Built-in TLS SMTP email dispatcher with photo attachment.

---

## 👤 Enrolling & Managing Trusted Faces

You can enroll trusted individuals (Owner, Family, Friends) in two easy ways:

### 1. Enroll via Live Webcam (Recommended)
Look straight at the webcam. This captures 5 multi-angle facial samples:
```powershell
python intruder_lens.py --enroll-face "Deepak"
```
You can repeat this for family members:
```powershell
python intruder_lens.py --enroll-face "Mom"
python intruder_lens.py --enroll-face "Brother"
```

### 2. Enroll from an Existing Photo on Disk
If you already have a clear picture:
```powershell
python intruder_lens.py --enroll-face-image "Deepak" "C:\path\to\photo.jpg"
```

### 3. View All Enrolled Trusted Faces
```powershell
python intruder_lens.py --list-faces
```

### 4. Remove a Person from the Whitelist
```powershell
python intruder_lens.py --remove-face "Brother"
```

---

## 🚀 Quick Start & CLI Tools

All captures are automatically saved to the [captures/](file:///e:/CLASSROOM/Sem-7\ADDITIONAL\IntruderLens\captures) directory.

### 1. Check System Health & Diagnostics
```powershell
python intruder_lens.py --status
```
Displays webcam status, face engine status, enrolled trusted profiles, and recent captures.

### 2. Test Camera Hardware
```powershell
python intruder_lens.py --test-camera
```

### 3. Simulate Laptop Lid-Open Event
```powershell
python intruder_lens.py --test-lid
```
*If an enrolled face is in front of the camera, it shows `ACCESS GRANTED` and suppresses the warning. If an unknown face is present, it captures evidence.*

### 4. Simulate 3x Wrong Password Attempts
```powershell
python intruder_lens.py --test-failed-logon
```

### 5. Run the Guard Daemon in Foreground
```powershell
python intruder_lens.py --run
```

---

## ⚙️ Configuration (`config.py`)

You can customize parameters directly in [config.py](file:///e:/CLASSROOM/Sem-7\ADDITIONAL\IntruderLens\config.py):

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `FACE_RECOGNITION_ENABLED` | `True` | Enable intelligent owner face recognition |
| `FACE_MATCH_THRESHOLD` | `0.35` | Cosine similarity threshold (0.32–0.363 recommended) |
| `IGNORE_AUTHORIZED_FACES` | `True` | Suppress photo alerts for recognized owner/family |
| `FAILED_ATTEMPT_THRESHOLD` | `3` | Number of failed password attempts before camera triggers |
| `ROLLING_WINDOW_SECONDS` | `120` | Time window (seconds) to accumulate failed attempts |
| `LID_OPEN_CAPTURE_ENABLED` | `True` | Enable/disable photo capture when lid is opened |
| `LID_COOLDOWN_SECONDS` | `20` | Anti-bounce cooldown between lid-open snapshots |
| `TELEGRAM_ENABLED` | `False` | Enable instant Telegram bot photo alerts |
| `SMTP_ENABLED` | `False` | Enable instant TLS SMTP email photo alerts |

---

## 🔒 Background Autostart Setup

To run IntruderLens completely silently in the background on startup with full webcam hardware access and administrative auditing privileges:

Open an **Elevated (Administrator) PowerShell** terminal and run:
```powershell
python intruder_lens.py --setup-task
```
