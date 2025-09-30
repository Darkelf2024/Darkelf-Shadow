# Darkelf Shadow Browser

**Darkelf Shadow** is a next-generation, privacy-hardened web browser built in Python and PyQt5. It’s designed from the ground up to maximize anonymity, security, anti-tracking, and anti-fingerprinting—out of the box. Darkelf Shadow incorporates deep Tor integration, aggressive ad/tracker defense, and state-of-the-art fingerprint resistance to protect your identity and browsing habits.

![Darkelf Shadow](https://github.com/Darkelf2024/Darkelf-Shadow/blob/main/Darkelf%20images/Darkelf%20Shadow%20Home.png)

---

## Why Darkelf Shadow?

Darkelf Shadow is not just another privacy browser—it is a comprehensive solution for users who demand advanced security, true anonymity, and robust defense against surveillance and web tracking. It combines multiple privacy layers, active and passive defenses, and usability-focused design, making it the ideal choice for privacy advocates, researchers, and anyone seeking secure browsing.

---

## Key Features

### 🛡️ **Hardened Security & Fingerprint Resistance**

- **Canvas Defense:** Dynamic randomization and spoofing of canvas fingerprints, with seed rotation and domain-aware bypass for major video sites.
- **WebGL Spoofing:** Vendor, renderer, and debug info are spoofed to mimic common configurations and defeat WebGL fingerprinting.
- **Audio/Battery/Font/Locale Protection:** Prevents fingerprinting via audio contexts, battery status, font enumeration, and locale/timezone leaks.
- **Letterboxing:** Forces all screen/window geometry to fixed sizes, blocking screen and viewport fingerprinting.
- **Strict WebRTC Lockdown:** Blocks WebRTC IP leakage, disables STUN, strips private/public IPs from SDP, and enforces relay-only transport.

### 🔒 **Tor Integration & Onion Routing**

- **Automatic Tor Startup:** Launches Tor with custom configuration, manages SOCKS/DNS proxying for both clearnet and .onion domains.
- **Tor DNS Routing:** Ensures DNS queries are anonymized, preventing local ISP leaks.
- **Onion Search:** DuckDuckGo onion search is used automatically when Tor is active.

### 🚫 **Ad & Tracker Blocking**

- **Network-Level Blocking:** Intercepts and blocks requests to known ad/tracker domains (Google, Facebook, analytics, etc.) before page load.
- **JavaScript-Based Ad Defense:** Removes overlays, blocks tracking scripts, and actively strips ads from YouTube and other major sites.
- **Invisible Tracker Removal:** Scans and removes 1x1 pixel images, tracking pixels, and hidden iframes.

### 🧬 **Advanced Anti-Fingerprinting**

- **User-Agent & Vendor Spoofing:** Dynamic spoofing of user-agent, platform, device memory, concurrency, and vendor strings—per-domain and per-tab.
- **Font & Locale Spoofing:** Ensures uniform font and locale presentation, randomizes metrics, and disables font queries.
- **Multi-Vector Defenses:** Disables media device enumeration, patches common JS APIs, and blocks fingerprinting attempts via computed styles, WebGL, and canvas.

### 🖥️ **Minimal, Modern UI**

- **Tabbed Browsing:** Compact, multi-tab interface with easy navigation and short labels.
- **Toolbar Shortcuts:** Navigation, zoom, fullscreen, new tab, JavaScript toggle, and one-click “Nuke” data wipe.
- **Custom Search:** DuckDuckGo homepage (clearnet or onion) and quick search integration.

### ⚡ **Usability & Control**

- **JavaScript Toggle:** Instantly enable/disable JS globally—defeating many tracking attempts.
- **Nuke Button:** Wipe all cookies, cache, and browsing history instantly for session privacy.
- Blocks ad overlays, skips video ads, and strips tracking payloads.

---

## Installation

### Prerequisites

- Python 3.8+
- PyQt5 (`pip install PyQt5 PyQtWebEngine`)
- [Tor](https://www.torproject.org/download/) installed and available in your PATH

### Clone & Run

```bash
git clone https://github.com/Darkelf2024/Darkelf-Shadow.git
cd Darkelf-Shadow
python Darkelf\ Shadow\.py
```

#### On Linux/macOS:

You may need to install Tor via your package manager:

```bash
# Ubuntu/Debian
sudo apt install tor
# macOS (Homebrew)
brew install tor
```

---

## Usage

- **Search or enter URL** in the address bar.
- Use the toolbar for navigation, zoom, fullscreen, new tab, and quick actions.
- Click the **Nuke** icon to erase browsing data.
- Toggle JavaScript with the JS icon.
- YouTube and other major sites are automatically hardened for privacy.

---

## Full Security Suite

- **Canvas, WebGL, Audio, Battery:** All major fingerprinting vectors are randomized or spoofed.
- **Font & Locale Protection:** Prevents font and locale probing.
- **Letterboxing:** Forces fixed window/screen sizes to defeat geometry fingerprinting.
- **Strict WebRTC Lockdown:** Prevents leaks of local/public IP via WebRTC.
- **Onion Routing & Tor:** All traffic routed via Tor when enabled, with .onion auto-support.
- **Multi-Tab Isolation:** Each tab uses its own fingerprint spoofing and privacy context.
- **Session Cleansing:** “Nuke” destroys all session traces in one click.

---

## Advanced Options

- **Onion Mode:** Automatically uses DuckDuckGo’s onion search when Tor is enabled.
- **Command-line/Env overrides:** Force Tor or proxy via flags:
  - `--tor` or `--use-tor`
  - `--proxy=socks5://127.0.0.1:9052`
  - `DARKELF_TOR=1` in environment

---

## Troubleshooting

- **Tor not found:** Make sure Tor is installed and available in your system PATH.
- **PyQt5 Errors:** Run `pip install PyQt5 PyQtWebEngine`.
- **Permissions:** Some features require filesystem write access for seed storage.

---

## Contributing

Pull requests, feedback, and issues are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

MIT License. See [LICENSE](LICENSE) for full text.

---

> **Darkelf Shadow**: Hardened, private, anti-fingerprint browsing for everyone.
