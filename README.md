<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=30&duration=3000&pause=1000&color=00D4FF&center=true&vCenter=true&width=600&lines=IntruderLens+%F0%9F%94%90;Physical+Security+for+Your+Laptop;Silently+Watches.+Instantly+Alerts." alt="IntruderLens" />

<br/>

```
  ___       _                 _           _
 |_ _| _ _ | |_  _ _  _  _  __| | ___  _ _ | |   ___  _ _   ___
  | | | ' \|  _|| '_|| || |/ _` |/ -_)| '_|| |__/ -_)| ' \ (_-<
 |___||_||_| \__||_|   \_,_|\__,_|\___||_|  |____\___||_||_|/__/
```

### 🔐 Stealth Physical Security Daemon for Windows — with Intelligent Face Whitelisting

<br/>

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![OpenCV](https://img.shields.io/badge/OpenCV-5.0-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org/)
[![License](https://img.shields.io/badge/License-MIT-F7DF1E?style=for-the-badge)](LICENSE)
[![Offline](https://img.shields.io/badge/Face%20AI-100%25%20Offline-00C851?style=for-the-badge&logo=tensorflow&logoColor=white)]()
[![Stars](https://img.shields.io/github/stars/Deepak-Anuragi/IntruderLens?style=for-the-badge&color=FFD700)](https://github.com/Deepak-Anuragi/IntruderLens/stargazers)

<br/>

> **"Someone tries to open your laptop without permission — IntruderLens silently photographs them and sends you the proof. If it's you or your family, it stays quiet."**

<br/>

[🚀 Quick Start](#-installation--setup) · [🧠 How It Works](#️-how-it-works) · [📋 Features](#-features) · [⚙️ Configuration](#️-configuration) · [🗺️ Roadmap](#️-roadmap)

</div>

---

## 🎯 The Problem It Solves

Ever left your laptop unattended and wondered:
- *"Did someone try to log into my laptop while I was away?"*
- *"Who opened my laptop while it was closed?"*

**IntruderLens answers both questions automatically — without you doing anything.**

It runs silently in the background, completely invisible to the intruder. The moment someone tries to access your laptop without permission, it snaps their photo and delivers it straight to your phone.

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🔑 Wrong Password Detection
Monitors Windows Security Event Log in real-time. If someone enters the wrong password **3 times within 2 minutes**, IntruderLens silently activates the webcam and photographs them.

</td>
<td width="50%">

### 💻 Lid-Open / Wake Detection
Hooks into Windows Kernel-Power events and Win32 power notifications. The **instant someone opens your closed laptop**, the camera captures who's sitting in front of it.

</td>
</tr>
<tr>
<td width="50%">

### 🧠 Intelligent Face Whitelisting
Using offline **YuNet + SFace ONNX** models, IntruderLens compares the detected face against enrolled trusted profiles (you, family, friends). **Authorized face = no alert. Unknown face = instant warning.**

</td>
<td width="50%">

### 📲 Instant Mobile Alerts
Delivers the intruder's photo to your phone in under 1 second via **Telegram Bot API** or **TLS SMTP Email** — complete with timestamp, trigger reason, and device name.

</td>
</tr>
<tr>
<td width="50%">

### 🤫 100% Stealth Operation
Runs with **zero visible windows**, zero taskbar icons, zero flashes. DirectShow headless camera capture with Laplacian variance sharpness scoring to always save the clearest frame.

</td>
<td width="50%">

### 🔒 100% Offline Face AI
All facial recognition runs **entirely on-device** using OpenCV ONNX runtime. No biometric data ever leaves your machine. No cloud APIs, no subscriptions, no internet required for recognition.

</td>
</tr>
</table>

---

## 🏗️ How It Works

```
     ┌──────────────────────┐         ┌──────────────────────────┐
     │   TRIGGER SOURCE 1   │         │    TRIGGER SOURCE 2      │
     │                      │         │                          │
     │  3x Wrong Passwords  │         │  Laptop Lid Opened /     │
     │  (Event ID 4625)     │         │  System Wake             │
     │  Windows Security    │         │  (Kernel-Power 507/107 + │
     │  Event Log           │         │   Win32 LidSwitch Hook)  │
     └──────────┬───────────┘         └───────────┬──────────────┘
                │                                  │
                └──────────────┬───────────────────┘
                               │
                               ▼
                 ┌─────────────────────────┐
                 │   Silent Camera Burst   │
                 │   DirectShow / OpenCV   │
                 │   Warmup → Burst 3x     │
                 │   Laplacian Sharpness   │
                 │   → Best Frame          │
                 └────────────┬────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │   Face Detection        │
                 │   YuNet ONNX (offline)  │
                 └────────────┬────────────┘
                              │
              ┌───────────────┴────────────────┐
              │                                │
         Face Found                       No Face Found
              │                                │
              ▼                                ▼
 ┌────────────────────────┐       ┌───────────────────────────┐
 │  SFace Embedding       │       │  Fallback: Unknown Person  │
 │  Cosine Similarity     │       │  Save photo + Send Alert   │
 │  vs Whitelist          │       └───────────────────────────┘
 └────────────┬───────────┘
              │
    ┌─────────┴──────────┐
    │                    │
 ✅ MATCH            ❌ NO MATCH
    │                    │
    ▼                    ▼
ACCESS GRANTED     🚨 INTRUDER
Suppress Alert     Save Evidence
Log silently       Send Telegram
                   Send Email
```

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Core daemon |
| **Face Detection** | OpenCV YuNet ONNX | Real-time CNN face detector |
| **Face Recognition** | OpenCV SFace ONNX | 128D facial embedding + cosine similarity |
| **Camera Capture** | OpenCV + DirectShow | Headless burst capture on Windows |
| **Event Monitoring** | pywin32 `win32evtlog` | Windows Security & System Event Log queries |
| **Power Notifications** | Win32 `RegisterPowerSettingNotification` | Real-time lid/wake hardware events |
| **Notifications** | Telegram Bot API + SMTP TLS | Instant photo alerts |
| **Service Runtime** | Windows Scheduled Task / NSSM | Silent background autostart |

---

## 📂 Project Structure

```
IntruderLens/
│
├── 📄 intruder_lens.py     # Core daemon: event listeners, camera pipeline, face decisions, CLI
├── 📄 face_engine.py       # Offline face detection (YuNet) + recognition (SFace) engine
├── 📄 config.py            # All settings — thresholds, paths, alert credentials
├── 📄 download_models.py   # One-command ONNX model downloader from OpenCV Zoo
├── 📄 service_wrapper.py   # Optional native pywin32 Windows Service wrapper
│
├── 📄 requirements.txt     # pip dependencies
├── 📄 README.md            # This file
├── 📄 LICENSE              # MIT License
│
├── 📁 captures/            # 🔴 Runtime: Intruder photos (gitignored — private)
├── 📁 logs/                # 🔴 Runtime: Operational logs (gitignored)
├── 📁 models/              # 🔴 Runtime: ONNX models (gitignored — download separately)
└── 📁 trusted_faces/       # 🔴 Runtime: Face embeddings (gitignored — biometric data)
```

> **Privacy First:** All runtime directories are permanently excluded from version control via `.gitignore`. Your photos and face data never leave your device.

---

## 🚀 Installation & Setup

### Prerequisites
- ✅ Windows 10 / 11
- ✅ Python 3.10 or higher → [Download](https://www.python.org/downloads/)
- ✅ A working webcam (built-in or USB)
- ✅ Git → [Download](https://git-scm.com/)

---

### Step 1 — Clone & Install Dependencies

```powershell
git clone https://github.com/Deepak-Anuragi/IntruderLens.git
cd IntruderLens
pip install -r requirements.txt
```

---

### Step 2 — Download Face Recognition Models

The ONNX models are not stored in the repo (too large). Download them automatically:

```powershell
python download_models.py
```

This downloads from the official [OpenCV Zoo](https://github.com/opencv/opencv_zoo):
| Model | Size | Purpose |
| :--- | :--- | :--- |
| `face_detection_yunet_2023mar.onnx` | ~227 KB | Ultra-fast CNN face detector |
| `face_recognition_sface_2021dec.onnx` | ~37 MB | High-accuracy face recognizer |

---

### Step 3 — Enable Windows Logon Auditing *(Run as Administrator)*

This tells Windows to log every failed login attempt, which IntruderLens reads:

```powershell
auditpol /set /subcategory:"Logon" /success:enable /failure:enable
auditpol /set /subcategory:"Credential Validation" /success:enable /failure:enable
```

---

### Step 4 — Enroll Your Trusted Faces

This is the step that makes IntruderLens **smart**. Enroll yourself so it knows your face:

```powershell
# Look straight at your webcam — captures 5 facial angle samples
python intruder_lens.py --enroll-face "Deepak"

# Optionally enroll family members
python intruder_lens.py --enroll-face "Mom"
python intruder_lens.py --enroll-face "Brother"

# Or enroll from an existing photo file
python intruder_lens.py --enroll-face-image "Deepak" "C:\Users\Deepak\photo.jpg"

# Verify who is enrolled
python intruder_lens.py --list-faces
```

---

### Step 5 — Run System Diagnostics

Verify every component is working before going live:

```powershell
python intruder_lens.py --status
```

Expected healthy output:
```
=================================================================
           IntruderLens System Diagnostics Report
=================================================================
[1] Administrative Privileges: YES (Can audit Security Log)
[2] Primary Webcam (Index 0): ONLINE & ACCESSIBLE
[3] Captures Directory: ...\captures (EXISTS & WRITABLE)
[4] Logs Directory:     ...\logs (EXISTS & WRITABLE)
[5] Face Recognition Engine: ONLINE (YuNet + SFace)
[6] Enrolled Trusted Profiles: 1
      - Deepak (5 face reference samples)
[7] Total Saved Snapshots: 0
-----------------------------------------------------------------
Wrong Password Threshold: 3 attempts in 120s
Lid-Open Capture Enabled: True (Cooldown: 20s)
Ignore Authorized Faces:  True
=================================================================
```

---

### Step 6 — Test Everything Without Locking Yourself Out

```powershell
# Test 1: Verify webcam capture works
python intruder_lens.py --test-camera

# Test 2: Simulate lid-open → runs face check → shows ACCESS GRANTED or INTRUDER alert
python intruder_lens.py --test-lid

# Test 3: Simulate 3 wrong passwords → triggers full capture pipeline
python intruder_lens.py --test-failed-logon
```

---

### Step 7 — Go Live

**Option A: Foreground mode** (terminal stays open, good for testing)
```powershell
python intruder_lens.py --run
```

**Option B: Silent Background Autostart** *(Recommended — start once, runs forever)*

Open **Administrator PowerShell** and run:
```powershell
python intruder_lens.py --setup-task
```
This installs a **Windows Scheduled Task** (`IntruderLensDaemon`) that:
- Launches silently on every login
- Runs with highest privileges (reads Security Event Log)
- Runs in your user desktop session (full webcam access)
- Requires zero interaction — just works

---

## 👤 Managing Trusted Faces

```powershell
# See all trusted enrolled profiles
python intruder_lens.py --list-faces

# Add someone new via webcam
python intruder_lens.py --enroll-face "Sister"

# Add someone from a photo file
python intruder_lens.py --enroll-face-image "Sister" "C:\photos\sister.jpg"

# Remove someone from whitelist
python intruder_lens.py --remove-face "Sister"
```

---

## 📲 Setting Up Telegram Alerts *(Optional but Recommended)*

Get the intruder's photo delivered to your phone in under 1 second:

1. Open Telegram → search **@BotFather** → send `/newbot`
2. Give your bot a name and username — copy the **Bot Token**
3. Start a chat with your bot, then visit:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
4. Copy your **`chat.id`** from the JSON response
5. Update `config.py`:
   ```python
   TELEGRAM_ENABLED = True
   TELEGRAM_BOT_TOKEN = "123456:ABC-your-token-here"
   TELEGRAM_CHAT_ID  = "987654321"
   ```

---

## ⚙️ Configuration

All settings live in `config.py`. Key parameters:

| Parameter | Default | Description |
| :--- | :---: | :--- |
| `FAILED_ATTEMPT_THRESHOLD` | `3` | Wrong passwords before camera triggers |
| `ROLLING_WINDOW_SECONDS` | `120` | Sliding time window (s) to count failures |
| `COOLDOWN_SECONDS` | `30` | Minimum gap between wrong-password captures |
| `LID_OPEN_CAPTURE_ENABLED` | `True` | Enable lid-open / wake detection |
| `LID_COOLDOWN_SECONDS` | `20` | Anti-bounce cooldown between lid-open captures |
| `LID_HARDWARE_SETTLE_SECONDS` | `0.8` | Delay after wake for USB camera to power up |
| `FACE_RECOGNITION_ENABLED` | `True` | Enable intelligent face whitelist comparison |
| `FACE_MATCH_THRESHOLD` | `0.35` | Cosine similarity cutoff (higher = stricter matching) |
| `IGNORE_AUTHORIZED_FACES` | `True` | Suppress all alerts when owner/family detected |
| `CAMERA_INDEX` | `0` | Webcam device index (0 = primary/built-in) |
| `TELEGRAM_ENABLED` | `False` | Enable Telegram Bot instant photo alerts |
| `SMTP_ENABLED` | `False` | Enable Email instant photo alerts |

---

## 🛡️ Privacy & Security Design

IntruderLens was designed with **privacy-first principles**:

- **🔒 Fully Local AI** — YuNet and SFace run entirely on-device via ONNX runtime. No biometric data ever leaves your machine.
- **🔒 No Cloud Dependencies** — Face recognition, detection, and matching all happen offline. Works without internet.
- **🔒 Gitignored Sensitive Data** — `captures/`, `trusted_faces/`, and `logs/` are permanently excluded from version control. Your photos and embeddings are yours alone.
- **🔒 Placeholder Credentials Only** — The committed `config.py` contains no real tokens or passwords.
- **🔒 Encrypted Alerts** — Telegram uses HTTPS. Email uses TLS STARTTLS. No plaintext transmission.

---

## 🗺️ Roadmap

- [x] Wrong password detection via Security Event Log (Event 4625/4624)
- [x] Laptop lid-open & system wake detection (Kernel-Power + Win32 hook)
- [x] Offline face detection with OpenCV YuNet ONNX
- [x] Offline face recognition with OpenCV SFace ONNX
- [x] Multi-user face enrollment (owner + unlimited family/friends)
- [x] Intelligent alert suppression for authorized faces
- [x] Silent headless DirectShow camera burst capture
- [x] Telegram Bot instant photo alerts
- [x] SMTP TLS email instant photo alerts
- [x] Windows Scheduled Task silent autostart
- [x] Built-in simulation & diagnostic CLI tools
- [ ] Discord Webhook alert support
- [ ] Mobile push notifications (Pushover / Pushbullet)
- [ ] Offline alert queue — auto-dispatch when Wi-Fi reconnects
- [ ] Low-light / dark room detection fallback policy
- [ ] Simple local web dashboard to browse capture history

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create** your feature branch:
   ```bash
   git checkout -b feature/discord-alerts
   ```
3. **Commit** your changes:
   ```bash
   git commit -m "Add Discord Webhook alert dispatcher"
   ```
4. **Push** to your branch:
   ```bash
   git push origin feature/discord-alerts
   ```
5. **Open a Pull Request** — describe what you built and why

For major changes, please open an issue first to discuss the approach.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Legal Disclaimer

IntruderLens is designed strictly for personal security use on **your own device**. Using it to record or monitor individuals without their knowledge or consent may be **illegal in your jurisdiction**. The author assumes no liability for misuse. Always comply with your local privacy and surveillance laws.

---

<div align="center">

**Built with ❤️ by [Deepak Anuragi](https://github.com/Deepak-Anuragi)**

*If this project helped you or impressed you, please consider giving it a* ⭐ *— it means a lot!*

[![GitHub stars](https://img.shields.io/github/stars/Deepak-Anuragi/IntruderLens?style=social)](https://github.com/Deepak-Anuragi/IntruderLens/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Deepak-Anuragi/IntruderLens?style=social)](https://github.com/Deepak-Anuragi/IntruderLens/network/members)

</div>
