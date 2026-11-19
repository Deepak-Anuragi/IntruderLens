<div align="center">

```
                                      ___       _                 _           _              
                                     |_ _| _ _ | |_  _ _  _  _  __| | ___  _ _ | |   ___  _ _   ___ 
                                      | | | ' \|  _|| '_|| || |/ _` |/ -_)| '_|| |__/ -_)| ' \ (_-< 
                                     |___||_||_| \__||_|   \_,_|\__,_|\___||_|  |____\___||_||_|/__/ 
```

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=24&duration=3000&pause=1000&color=00D4FF&center=true&vCenter=true&width=550&lines=Physical+Security+for+Your+Laptop;Silently+Watches.+Instantly+Alerts.;100%25+Offline+Face+Recognition." alt="IntruderLens" />

<br/>

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
Sends the intruder's photo to your phone via **WhatsApp** (Twilio), **Email** (SMTP), or both. Each alert is short: what happened, when, and on which device. You can turn each channel on or off, or turn both off to only save photos to disk. Alerts are sent on a background thread, so the daemon keeps watching while they go out.

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
<tr>
<td colspan="2">

### 🛡️ Guard Mode — Shortcut-Activated Watch Mode
Stepping away for a minute without locking? Press your custom hotkey (default **`Ctrl+Shift+G`**) or type a secret password to arm Guard Mode. The moment **a face appears, a key is pressed, or the mouse/touchpad is touched**, IntruderLens silently snaps a photo. Owner's face = photo discarded. Anyone else = saved + alert sent.

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
Log silently       Send WhatsApp
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
| **Notifications** | Twilio WhatsApp API + SMTP STARTTLS | Photo alerts on a background thread |
| **Service Runtime** | Windows Scheduled Task / NSSM | Silent background autostart |

---

## 📂 Project Structure

```
IntruderLens/
│
├── 📄 intruder_lens.py     # Core daemon: event listeners, camera pipeline, face decisions, CLI
├── 📄 face_engine.py       # Offline face detection (YuNet) + recognition (SFace) engine
├── 📄 guard_mode.py        # Guard Mode: hotkey/password listener, input & face triggers
├── 📄 notification_dispatcher.py  # WhatsApp (Twilio) + Email (SMTP) alert sender
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
python intruder_lens.py --enroll-face "Deepak" --image "C:\Users\Deepak\photo.jpg"

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

# Test 4: Arm Guard Mode immediately → touch keyboard/mouse or show your face
python intruder_lens.py --test-guard
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
python intruder_lens.py --enroll-face "Sister" --image "C:\photos\sister.jpg"

# Remove someone from whitelist
python intruder_lens.py --remove-face "Sister"
```

---

## 🛡️ Using Guard Mode

Guard Mode starts listening automatically with the daemon (`--run` / scheduled task). The screen stays unlocked; you simply arm it before walking away.

| Action | Default |
| :--- | :--- |
| Activate Guard Mode | `Ctrl+Shift+G` |
| Deactivate Guard Mode | `Ctrl+Shift+S` |

After activation there is a **5 s arming delay** so you can step away. Once armed, any of these triggers a silent capture (each can be toggled in `config.py`):

- 👤 a face appears in front of the webcam
- ⌨️ any key is pressed
- 🖱️ the mouse/touchpad is moved, clicked or scrolled

Every capture goes through face recognition: **your face → photo discarded, nothing saved**; anyone else (or no face visible) → saved to `captures/guard_*.jpg` and a WhatsApp/Email alert is sent.

> Keyboard/mouse triggers wait a short grace period (`GUARD_MODE_INPUT_GRACE_SECONDS`, 2 s) before capturing. If you deactivate within that window, the capture is cancelled — so your own deactivation keystrokes never cause an alert.

**Customize the controls** in `config.py` or from the CLI (CLI values are saved to the git-ignored `intruder_lens.ini` and override `config.py`):

```powershell
# Custom hotkeys — 2 or 3 simultaneous keys each (same key for both = toggle)
python intruder_lens.py --set-guard-shortcuts ctrl+alt+g ctrl+alt+u

# Use a typed password instead (typed anywhere, no Enter needed)
python intruder_lens.py --set-guard-password mysecret            # same password toggles on/off
python intruder_lens.py --set-guard-password armme disarmme      # separate passwords

# Switch back to hotkeys
python intruder_lens.py --use-guard-shortcuts
```

> **Note:** Guard Mode needs the interactive desktop session (global keyboard/mouse hooks), so run it via `--run` or `--setup-task`, not the Session-0 Windows Service wrapper.

---

## 📲 Setting Up WhatsApp & Email Alerts *(Optional but Recommended)*

When an intruder photo is saved, IntruderLens sends you a short alert:

```
Intruder Lens Alert

Activity : Unknown face detected while Guard Mode was active
Time     : 20 Nov 2026, 09:41 PM
Device   : MY-LAPTOP

[Photo attached]
Stay safe.
```

| Trigger | Activity text |
| :--- | :--- |
| Wrong passwords | 3 consecutive wrong password attempts detected |
| Lid open / wake | Laptop lid opened or woken from sleep |
| Guard Mode — face | Unknown face detected while Guard Mode was active |
| Guard Mode — keyboard | Keyboard activity detected while Guard Mode was active |
| Guard Mode — mouse | Mouse/touchpad activity detected while Guard Mode was active |

Pick your channels in `config.py`:

| `NOTIFY_VIA_WHATSAPP` | `NOTIFY_VIA_EMAIL` | Result |
| :---: | :---: | :--- |
| `True` | `False` | WhatsApp only |
| `False` | `True` | Email only |
| `True` | `True` | Both |
| `False` | `False` | Silent mode: photo is only saved to disk |

### 🔐 Where to put your credentials

`config.py` is committed to git, so keep **only placeholders** in it. Put real values in the git-ignored `intruder_lens.ini`, using lower-case key names:

```ini
[notifications]
notify_via_whatsapp = true
notify_via_email = true
twilio_account_sid = ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
twilio_auth_token = your-real-token
owner_whatsapp_number = whatsapp:+91XXXXXXXXXX
smtp_username = you@gmail.com
smtp_password = abcd efgh ijkl mnop
owner_email = you@gmail.com
```

You can also use environment variables prefixed with `INTRUDERLENS_`, such as `INTRUDERLENS_SMTP_PASSWORD`. Environment variables override the `.ini` file, and the `.ini` file overrides `config.py`.

### WhatsApp (Twilio Sandbox)

1. Create a free account at [twilio.com](https://www.twilio.com/). From the Console, copy your **Account SID** and **Auth Token**.
2. Go to **Messaging → Try it out → Send a WhatsApp message**. Send the `join <code>` message it shows from your phone to the sandbox number (`+1 415 523 8886`).
3. Set `twilio_account_sid`, `twilio_auth_token` and `owner_whatsapp_number` (e.g. `whatsapp:+919876543210`), then set `notify_via_whatsapp = true`.

> **About the photo:** Twilio can only attach an image from a public URL. Before sending, IntruderLens uploads the photo to a temporary host that deletes it after 1 hour (`WHATSAPP_IMAGE_HOST = "litterbox"` by default, or `"imgbb"` with an `IMGBB_API_KEY`). Anyone who has that link can open the photo until it expires. Set `WHATSAPP_IMAGE_HOST = "none"` to send text-only WhatsApp alerts. If the upload fails, the text alert is still sent. The photo is always attached directly to emails.
>
> Sandbox sessions expire if you don't message the sandbox for 72 hours. Send `join <code>` again to re-activate.

### Email (SMTP)

| Provider | `SMTP_HOST` | `SMTP_PORT` |
| :--- | :--- | :---: |
| Gmail | `smtp.gmail.com` | `587` |
| Outlook / Office 365 | `smtp.office365.com` | `587` |

For Gmail, turn on 2-Step Verification, then create an **App Password** at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords). Use that as `smtp_password`, **not** your normal password. The email subject is `IntruderLens Alert — <activity>` and the photo is attached.

### Test it

```powershell
python intruder_lens.py --test-alert   # sends a test alert with your newest capture
python intruder_lens.py --status       # shows which channels are enabled
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
| `IGNORE_AUTHORIZED_FACES` | `True` | Skip saving and alerting when every face in the photo is enrolled (a stranger next to the owner still triggers an alert). `False` saves and alerts for trusted faces too |
| `CAMERA_INDEX` | `0` | Webcam device index (0 = primary/built-in) |
| `GUARD_MODE_ENABLED` | `True` | Start the Guard Mode listener with the daemon |
| `GUARD_MODE_ACTIVATE_SHORTCUT` | `"ctrl+shift+g"` | Hotkey to arm Guard Mode |
| `GUARD_MODE_DEACTIVATE_SHORTCUT` | `"ctrl+shift+s"` | Hotkey to disarm Guard Mode |
| `GUARD_MODE_USE_PASSWORD` | `False` | Use a typed password instead of hotkeys |
| `GUARD_MODE_PASSWORD` | `""` | Activation password (also deactivates unless a separate one is set) |
| `GUARD_MODE_DEACTIVATE_PASSWORD` | `""` | Optional separate deactivation password |
| `GUARD_MODE_TRIGGER_ON_FACE` / `_KEYPRESS` / `_MOUSE` | `True` | Which activity triggers a capture |
| `GUARD_MODE_ARM_DELAY_SECONDS` | `5.0` | Time to step away after activating |
| `GUARD_MODE_COOLDOWN_SECONDS` | `10.0` | Minimum gap between Guard Mode captures |
| `NOTIFY_VIA_WHATSAPP` | `False` | Send WhatsApp alerts via Twilio |
| `NOTIFY_VIA_EMAIL` | `False` | Send Email alerts via SMTP |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | placeholder | Twilio credentials (put real values in `intruder_lens.ini`) |
| `TWILIO_WHATSAPP_FROM` | `"whatsapp:+14155238886"` | Twilio sandbox sender |
| `OWNER_WHATSAPP_NUMBER` | placeholder | Your WhatsApp number, e.g. `whatsapp:+91…` |
| `WHATSAPP_IMAGE_HOST` | `"litterbox"` | Temporary photo host for WhatsApp: `litterbox`, `imgbb`, or `none` |
| `SMTP_HOST` / `SMTP_PORT` | `smtp.gmail.com` / `587` | SMTP server (Outlook: `smtp.office365.com`) |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | placeholder | SMTP login (Gmail: use an App Password) |
| `OWNER_EMAIL` | placeholder | Where alert emails go |

---

## 🛡️ Privacy & Security Design

IntruderLens was designed with **privacy-first principles**:

- **🔒 Fully Local AI** — YuNet and SFace run entirely on-device via ONNX runtime. No biometric data ever leaves your machine.
- **🔒 No Cloud Dependencies** — Face recognition, detection, and matching all happen offline. Works without internet.
- **🔒 Gitignored Sensitive Data** — `captures/`, `trusted_faces/`, and `logs/` are permanently excluded from version control. Your photos and embeddings are yours alone.
- **🔒 Placeholder Credentials Only** — The committed `config.py` contains no real tokens or passwords. Real credentials go in the git-ignored `intruder_lens.ini` or in environment variables.
- **🔒 Encrypted Alerts** — Twilio and photo uploads use HTTPS, and Email uses STARTTLS. Nothing is sent in plaintext. For WhatsApp, the photo sits on a temporary public link for up to 1 hour. Set `WHATSAPP_IMAGE_HOST = "none"` to avoid this.

---

## 🗺️ Roadmap

- [x] Wrong password detection via Security Event Log (Event 4625/4624)
- [x] Laptop lid-open & system wake detection (Kernel-Power + Win32 hook)
- [x] Offline face detection with OpenCV YuNet ONNX
- [x] Offline face recognition with OpenCV SFace ONNX
- [x] Multi-user face enrollment (owner + unlimited family/friends)
- [x] Intelligent alert suppression for authorized faces
- [x] Silent headless DirectShow camera burst capture
- [x] WhatsApp photo alerts (Twilio)
- [x] SMTP email photo alerts (Gmail / Outlook)
- [x] Choose alert channels independently: WhatsApp, Email, both, or silent
- [x] Windows Scheduled Task silent autostart
- [x] Built-in simulation & diagnostic CLI tools
- [x] Guard Mode — hotkey/password-armed watch mode (face, keyboard, mouse/touchpad triggers)
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
