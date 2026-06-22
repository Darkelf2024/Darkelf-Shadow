# 🕶️ Darkelf Shadow  [![PyPI Downloads](https://static.pepy.tech/personalized-badge/darkelf-shadow?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/darkelf-shadow)

**Fully Hardened • Ephemeral • Zero-Trace Browser (Qt WebEngine / Chromium Core)**

Darkelf Shadow v4.6.2 is a defense-in-depth, privacy-hardened web browser engineered to eliminate persistent tracking, reduce attack surface, and actively defend against modern web threats — all while operating entirely in-memory.

---

## ⬇️ Install

Darkelf Shadow runs on Linux and Windows, and you do not need to be technical to set it up. Pick the option that matches your computer.

### Linux

The AppImage is one file that runs on most Linux distributions. There is nothing to install and nothing to clean up later.

1. Open the [latest release](https://github.com/oracle-actual/Darkelf-Shadow/releases/latest) and download the file that ends in `.AppImage`.
2. Allow it to run. Right click the file, open Properties, and turn on "Allow executing file as program". If you like the terminal instead:
   ```bash
   chmod +x Darkelf-Shadow-*.AppImage
   ```
3. Double click the file to start browsing. Keep it wherever you want and open it again any time.

If a double click does nothing, your system is missing FUSE. Install it with `sudo apt install libfuse2`, then try again.

### Windows

1. Open the [latest release](https://github.com/oracle-actual/Darkelf-Shadow/releases/latest) and download `DarkelfShadow-Setup.exe`.
2. Run it and follow the prompts. It adds Darkelf Shadow to your Start menu.
3. Open Darkelf Shadow from the Start menu.

Prefer not to install? Grab the portable ZIP from the same page, unzip it, and open `DarkelfShadow.exe`.

### Python users (pip) v4.6.2 is still current

If you already have Python 3.10 or newer (up to 3.14), install it straight from PyPI:

```bash
pip install darkelf-shadow
darkelf-shadow
```

Every release ships a Windows build and a Linux build together, so you get the same browser on both.

---

## 🧱 HARDENED BY DESIGN

Darkelf Shadow is not just private — it is architecturally hardened:

### 🔥 Zero Persistence Architecture
- No disk-based session storage  
- Full memory-only browsing lifecycle  
- Automatic purge on process exit  

### 🛡️ Network-Level Enforcement
- Deep request interception layer  
- Pre-flight blocking before rendering  
- Third-party isolation logic  

### 🧠 Autonomous Threat Detection (MiniAI)
- On-device behavioral analysis  
- No cloud dependency  
- Real-time adaptive defense  

### 🚫 Telemetry-Free Core
- No analytics, tracking, or external communication  
- No hidden background services  

---

## 🚀 HARDENED FEATURE SET

### 🔐 Ephemeral Session Engine
- Memory-only:
  - Cookies  
  - Cache  
  - LocalStorage  
  - IndexedDB  
- No recovery artifacts  
- No session residue  

---

### 🧠 MiniAI Sentinel (Active Defense Engine)

Fully integrated on-device security AI:

#### 🚨 Intrusion Detection
- SQL Injection  
- XSS  
- Command Injection  
- Path Traversal  

#### 🦠 Detection Capabilities
- Malware / Exploit Detection  
- Tracker & Surveillance Detection  
- Fingerprinting Monitoring  
- Behavioral anomaly detection (burst/flood attacks)  

---

### ⚡ Automated Response Modes

| Mode | Behavior |
|------|--------|
| 🟢 Standby | Passive monitoring |
| 🔴 Lockdown | Blocks all suspicious traffic |
| 🚨 Panic Mode | Full network shutdown |

---

### 🌐 Advanced Network Filtering
- ✔ EasyList / EasyPrivacy / uBlock filters  
- ✔ Regex-based ABP engine  
- ✔ Heuristic tracker detection  
- ✔ Hard-blocked known ad/tracker domains  
- ✔ Third-party request classification  

---

### 🔍 Anti-Tracking & URL Sanitization
Removes:
- utm_*  
- fbclid  
- gclid  
- Tracking campaign parameters  

Prevents cross-site tracking correlation  

---

### 🔐 HTTPS Enforcement Layer
- Automatic HTTP → HTTPS upgrade  
- HSTS-like memory tracking  
- Downgrade attack prevention  

---

### 🎭 Fingerprint Resistance Layer
MiniAI actively detects and neutralizes:

- Canvas fingerprinting → Noise injection  
- WebGL → Spoofed output  
- AudioContext → Sanitized  
- Fonts → Obfuscated  
- WebRTC → Disabled  
- Geolocation → Blocked  

---

### 📥 Secure Download Isolation
- Sandboxed download directory  
- Randomized filenames (anti-forensics)  
- Optional ephemeral storage  
- No metadata leakage  

---

### ⚙️ Chromium Hardening Flags

Disabled by default:

- ❌ Sync services  
- ❌ Metrics collection  
- ❌ Crash reporting  
- ❌ First-run tracking  

---

## 🧩 DEFENSE-IN-DEPTH MODEL

Darkelf Shadow combines multiple security layers:

- Request Interception Layer  
- Filter Engine (EasyList + Heuristics)  
- MiniAI Behavioral Analysis  
- Fingerprint Protection  
- Ephemeral Storage Model  

Each layer operates independently and reinforces the others.

---

## 🧪 THREAT INTELLIGENCE CAPABILITIES

MiniAI provides:

- 📊 Threat scoring system  
- 📈 Real-time event monitoring  
- 🧠 Domain risk caching  
- 📋 Detailed threat reports  
- 🔄 Adaptive escalation logic  

---

## ⚡ PERFORMANCE CHARACTERISTICS

- ⚙ Built on PySide6 + Qt WebEngine  
- 🚀 Chromium rendering engine  
- 🧠 In-memory operations (minimal disk I/O)  
- ⚡ Fast startup, clean shutdown  

---

## 🔒 SECURITY POSTURE SUMMARY

| Category | Status |
|----------|--------|
| Persistence | ❌ None |
| Telemetry | ❌ None |
| Tracking Resistance | ✅ Strong |
| Fingerprint Defense | ✅ Active |
| Threat Detection | ✅ Real-time |
| Network Control | ✅ Enforced |

---

## ⚠️ OPERATIONAL SECURITY NOTES

For maximum protection, combine Darkelf Shadow with:

- 🔐 Full-disk encryption (FileVault, LUKS)  
- 🔥 OS-level firewall rules  
- 🧱 Sandboxed runtime environment  
- 🌐 Trusted VPN or network isolation  

---

## 📜 LICENSE

Licensed under **LGPL-3.0-or-later**

---

## ⚠️ DISCLAIMER

This software is provided **“AS IS”** without warranty.

- Does not guarantee anonymity  
- Does not replace OS-level security  
- Intended for advanced users and hardened environments  

---

## 👤 AUTHOR

**Dr. Kevin Moore (2025)**  
Darkelf Project — Shadow Edition

## Special Thanks 

Thank You - Mecha Comet Team, Tim Burns, Oracle-actual and 404 Yeti!
