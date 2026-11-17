<div align="center">

```
  ___       _                 _           _                      
 |_ _| _ _ | |_  _ _  _  _  __| | ___  _ _ | |   ___  _ _   ___  
  | | | ' \|  _|| '_|| || |/ _` |/ -_)| '_|| |__/ -_)| ' \ (_-<  
 |___||_||_| \__||_|   \_,_|\__,_|\___||_|  |____\___||_||_|/__/  
```

# IntruderLens

**Stealth Windows Physical Security Daemon with Intelligent Face Whitelisting**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![OpenCV](https://img.shields.io/badge/OpenCV-5.0-green?logo=opencv&logoColor=white)](https://opencv.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Offline](https://img.shields.io/badge/Face%20Recognition-100%25%20Offline-brightgreen)]()

*Silently watches your laptop. Snaps the intruder. Sends you the proof.*

</div>

---

## 📖 What Is IntruderLens?

IntruderLens is a lightweight, 100% offline stealth security daemon for Windows 10/11 laptops. It runs silently in the background and automatically:

1. **Detects when someone types your password wrong 3 times** → takes their photo
2. **Detects when someone opens your closed laptop lid** → takes their photo
3. **Checks if the person is you or a trusted family member** → if yes, suppresses the alert silently
4. **If it's a stranger** → saves the evidence photo and sends you an instant alert on Telegram / Email

No GUI. No pop-ups. No flashes. The intruder never knows they were photographed.

---

## ✨ Features

| Feature | Details |
| :--- | :--- |
| 🔑 **Wrong Password Detection** | Monitors Windows Security Event Log (Event ID 4625). Triggers after 3 failed attempts within 120s rolling window |
| 💻 **Lid-Open / Wake Detection** | Hooks into Kernel-Power events (ID 507, 107) and Win32 `GUID_LIDSWITCH_STATE_CHANGE` real-time power notifications |
| 🧠 **Face Recognition Whitelist** | Offline YuNet (detector) + SFace (recognizer) ONNX models. Enroll owner + unlimited family members |
| 🤫 **Smart Alert Suppression** | If face matches whitelist → no photo saved, no alert sent. `ACCESS GRANTED` logged silently |
| 📸 **Silent Headless Camera** | DirectShow multi-frame burst capture. Laplacian variance sharpness scoring. Zero GUI windows |
| 📲 **Telegram Alerts** | Instant photo + metadata pushed to your phone via Telegram Bot API |
| 📧 **Email Alerts** | TLS SMTP email with intruder photo attached |
| 🔄 **Auto-Start on Login** | Windows Scheduled Task with highest privileges — starts silently on every logon |

---

## 🏗️ How It Works

```
Trigger Event
     │
     ├─── 3x Wrong Passwords  ──┐
     │    (Event ID 4625)        │
     │                           ▼
     └─── Lid Opened / Wake ──► Capture Webcam Burst (DirectShow, silent)
          (Kernel-Power 507/107)        │
                                        ▼
                              Select Sharpest Frame
                              (Laplacian Variance Score)
                                        │
                                        ▼
                              ┌─── Face Detected? ───┐
                              │                       │
                             YES                      NO
                              │                       │
                              ▼                       ▼
                     Match Against              Fallback Policy:
                     Whitelist (SFace           Treat as Unknown
                     Cosine Similarity)         → Alert + Save
                              │
              ┌───── Match? ──────────┐
              │                       │
           ✅ YES                   ❌ NO
              │                       │
    ACCESS GRANTED            🚨 INTRUDER DETECTED
    Suppress Alert            Save Evidence Photo
    Log silently              Send Telegram / Email Alert
```

---

## 📂 Project Structure

```
IntruderLens/
│
├── intruder_lens.py       # Main daemon: event listeners, camera engine, face pipeline, CLI
├── face_engine.py         # Offline face detection (YuNet) + recognition (SFace) engine
├── config.py              # All settings: thresholds, paths, alert credentials
├── download_models.py     # Auto-downloads ONNX model files from OpenCV Zoo
├── service_wrapper.py     # Native pywin32 Windows Service wrapper (optional)
│
├── requirements.txt       # Python dependencies
├── SETUP.md               # Step-by-step installation guide
├── LICENSE                # MIT License
│
├── captures/              # Runtime: Intruder photos saved here (gitignored)
├── logs/                  # Runtime: Operational logs (gitignored)
├── models/                # Runtime: ONNX models downloaded here (gitignored)
└── trusted_faces/         # Runtime: Enrolled face embeddings (gitignored)
```

> **Privacy Note:** `captures/`, `trusted_faces/`, `logs/`, and `models/` are all excluded from git. Your photos and biometric data never leave your machine.

---

## ⚡ Quick Install

### Prerequisites
- Windows 10 / 11
- Python 3.10 or higher
- A working webcam

### 1. Clone & Install Dependencies
```powershell
git clone https://github.com/Deepak-Anuragi/IntruderLens.git
cd IntruderLens
pip install -r requirements.txt
```

### 2. Download Face Recognition Models
```powershell
python download_models.py
```
Downloads two offline ONNX models from the official [OpenCV Zoo](https://github.com/opencv/opencv_zoo):
- `face_detection_yunet_2023mar.onnx` — ~227 KB, ultra-fast CNN face detector
- `face_recognition_sface_2021dec.onnx` — ~37 MB, high-accuracy face recognizer

### 3. Enable Windows Logon Auditing *(Run as Administrator)*
```powershell
auditpol /set /subcategory:"Logon" /success:enable /failure:enable
auditpol /set /subcategory:"Credential Validation" /success:enable /failure:enable
```

### 4. Enroll Your Face
```powershell
# Enroll yourself (look straight at the webcam — captures 5 angles)
python intruder_lens.py --enroll-face "YourName"

# Enroll family members
python intruder_lens.py --enroll-face "Mom"
python intruder_lens.py --enroll-face "Brother"

# Or enroll from an existing photo
python intruder_lens.py --enroll-face-image "YourName" "C:\path\to\photo.jpg"
```

### 5. Verify Setup
```powershell
python intruder_lens.py --status
```

### 6. Run
```powershell
# Foreground (visible terminal)
python intruder_lens.py --run

# OR: Silent background autostart on every login (Recommended)
# Run from Administrator PowerShell:
python intruder_lens.py --setup-task
```

> 📖 See [SETUP.md](SETUP.md) for the full detailed installation guide.

---

## 🧪 Testing & Simulation

You can verify every feature without locking yourself out:

```powershell
# Test webcam snapshot
python intruder_lens.py --test-camera

# Simulate laptop lid-open (runs face check → shows ACCESS GRANTED or INTRUDER alert)
python intruder_lens.py --test-lid

# Simulate 3 wrong password attempts (triggers capture pipeline)
python intruder_lens.py --test-failed-logon

# Full system diagnostics
python intruder_lens.py --status
```

---

## 👤 Managing Trusted Faces

```powershell
# List all enrolled profiles
python intruder_lens.py --list-faces

# Add someone from live webcam
python intruder_lens.py --enroll-face "Sister"

# Add someone from a photo file
python intruder_lens.py --enroll-face-image "Sister" "C:\photos\sister.jpg"

# Remove someone from whitelist
python intruder_lens.py --remove-face "Sister"
```

---

## ⚙️ Configuration

Edit `config.py` to customize behaviour:

| Parameter | Default | Description |
| :--- | :---: | :--- |
| `FAILED_ATTEMPT_THRESHOLD` | `3` | Wrong password attempts before camera triggers |
| `ROLLING_WINDOW_SECONDS` | `120` | Sliding time window (s) to count failures |
| `COOLDOWN_SECONDS` | `30` | Min gap between successive wrong-password captures |
| `LID_OPEN_CAPTURE_ENABLED` | `True` | Enable lid-open / wake detection |
| `LID_COOLDOWN_SECONDS` | `20` | Anti-bounce cooldown between lid-open captures |
| `LID_HARDWARE_SETTLE_SECONDS` | `0.8` | Delay after wake for USB camera to power up |
| `FACE_RECOGNITION_ENABLED` | `True` | Enable face whitelist comparison |
| `FACE_MATCH_THRESHOLD` | `0.35` | Cosine similarity cutoff (higher = stricter) |
| `IGNORE_AUTHORIZED_FACES` | `True` | Suppress alerts when owner/family detected |
| `CAMERA_INDEX` | `0` | Webcam device index |
| `TELEGRAM_ENABLED` | `False` | Send Telegram Bot photo alerts |
| `TELEGRAM_BOT_TOKEN` | `""` | Your Telegram Bot token |
| `TELEGRAM_CHAT_ID` | `""` | Your Telegram chat/user ID |
| `SMTP_ENABLED` | `False` | Send email alerts via TLS SMTP |
| `SMTP_USER` | `""` | Sender email address |
| `SMTP_PASSWORD` | `""` | App password (not your login password) |
| `SMTP_RECIPIENT` | `""` | Recipient email address |

---

## 📲 Setting Up Telegram Alerts *(Optional)*

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`, give it a name and username
3. Copy the **Bot Token** you receive
4. Start a chat with your new bot, then visit:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
5. Find your **chat id** in the response JSON
6. Update `config.py`:
   ```python
   TELEGRAM_ENABLED = True
   TELEGRAM_BOT_TOKEN = "123456:ABC-your-token-here"
   TELEGRAM_CHAT_ID = "987654321"
   ```

---

## 🛡️ Privacy & Security Design

- **100% Offline Face Recognition** — YuNet and SFace run entirely on-device. No biometric data ever leaves your machine.
- **Captures are local-only** — All `captures/*.jpg` are saved to your local drive only, never uploaded anywhere unless you configure Telegram/Email.
- **Biometric data gitignored** — `trusted_faces/` and `captures/` are permanently excluded from version control.
- **Placeholder credentials only** — `config.py` in this repo contains no real tokens or passwords.
- **NTFS ACL hardening** — Capture and log directories can be locked to `SYSTEM` and `Administrators` only.

---

## 🗺️ Roadmap

- [x] Wrong password detection (Event ID 4625/4624)
- [x] Laptop lid-open & system wake detection
- [x] Offline face recognition & owner whitelisting
- [x] Multi-user face enrollment (owner + family)
- [x] Telegram Bot instant photo alerts
- [x] SMTP Email instant photo alerts
- [x] Silent headless DirectShow camera capture
- [x] Windows Scheduled Task autostart
- [ ] Discord Webhook alert support
- [ ] Mobile push notifications (Pushover / Pushbullet)
- [ ] Offline alert queue (auto-send when Wi-Fi reconnects)
- [ ] Dark room / low-light face detection fallback
- [ ] Simple web dashboard to view captures

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Add my feature"`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Legal Disclaimer

IntruderLens is designed for personal security on **your own device**. Using it to record or monitor individuals without their knowledge or consent may be **illegal in your jurisdiction**. The author assumes no liability for misuse. Always comply with your local laws regarding surveillance and privacy.

---

<div align="center">

Made with ❤️ by [Deepak Anuragi](https://github.com/Deepak-Anuragi)

⭐ Star this repo if you found it useful!

</div>
