# IntruderLens — Setup Guide

Follow these steps after cloning the repository to get IntruderLens running on your Windows laptop.

---

## Step 1: Clone the Repository
```powershell
git clone https://github.com/Deepak-Anuragi/IntruderLens.git
cd IntruderLens
```

---

## Step 2: Install Python Dependencies
Make sure you have **Python 3.10+** installed, then run:
```powershell
pip install -r requirements.txt
```

---

## Step 3: Download the Face Recognition Models
The ONNX model files are not included in the repo (large binary files).
Download them automatically with:
```powershell
python download_models.py
```
This downloads:
- `models/face_detection_yunet_2023mar.onnx` — YuNet Face Detector (~227 KB)
- `models/face_recognition_sface_2021dec.onnx` — SFace Face Recognizer (~37 MB)

---

## Step 4: Enable Windows Logon Failure Auditing
Run this in an **Administrator PowerShell** so Windows logs failed password attempts:
```powershell
auditpol /set /subcategory:"Logon" /success:enable /failure:enable
auditpol /set /subcategory:"Credential Validation" /success:enable /failure:enable
```

---

## Step 5: Enroll Your Trusted Faces
Enroll your own face (and optionally family members) so IntruderLens knows who you are:
```powershell
# Enroll yourself via live webcam (look straight at the camera)
python intruder_lens.py --enroll-face "YourName"

# Or enroll from an existing photo
python intruder_lens.py --enroll-face-image "YourName" "C:\path\to\photo.jpg"

# View all enrolled trusted faces
python intruder_lens.py --list-faces
```

---

## Step 6: Run System Diagnostics
Verify everything is working:
```powershell
python intruder_lens.py --status
```

Expected output:
```
[1] Administrative Privileges: YES
[2] Primary Webcam (Index 0): ONLINE & ACCESSIBLE
[3] Captures Directory: ... (EXISTS & WRITABLE)
[5] Face Recognition Engine: ONLINE (YuNet + SFace)
[6] Enrolled Trusted Profiles: 1
```

---

## Step 7: Test Both Features
```powershell
# Test webcam snapshot
python intruder_lens.py --test-camera

# Test lid-open detection & face recognition
python intruder_lens.py --test-lid

# Test 3x wrong password detection
python intruder_lens.py --test-failed-logon
```

---

## Step 8: Run the Live Daemon

### Option A: Foreground (Console visible)
```powershell
python intruder_lens.py --run
```

### Option B: Silent Background Autostart (Recommended)
Run from an **elevated Administrator PowerShell**:
```powershell
python intruder_lens.py --setup-task
```
This installs a Windows Scheduled Task that launches IntruderLens silently on every login with full privileges.

---

## Optional: Enable Telegram / Email Alerts
Edit `config.py` and set your credentials:
```python
# Telegram
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = "your-bot-token"
TELEGRAM_CHAT_ID = "your-chat-id"

# Email
SMTP_ENABLED = True
SMTP_USER = "your-email@gmail.com"
SMTP_PASSWORD = "your-app-password"
SMTP_RECIPIENT = "alerts@example.com"
```
