# Darkelf Shadow Browser

**Darkelf Shadow** is a hardened, privacy-focused web browser built using Python and PyQt5. It is designed for maximum anonymity, anti-tracking, ad blocking, and anti-fingerprinting out of the box. With deep Tor integration, advanced anti-fingerprint JS injection, and aggressive ad/tracker defense, Darkelf Shadow is perfect for those who want true web privacy without the heavy overhead of traditional privacy browsers.

## 🔒 Key Features

- **Maximum Anonymity**: Built with privacy-first architecture
- **Anti-Tracking**: Blocks tracking scripts and cookies
- **Ad Blocking**: Aggressive ad and tracker defense
- **Anti-Fingerprinting**: JavaScript injection to prevent browser fingerprinting
- **Tor Integration**: Optional Tor routing for enhanced anonymity
- **Lightweight**: Not as heavy as traditional browsers while maintaining security
- **Custom User Agent**: Randomized user agents to prevent tracking
- **HTTPS Enforcement**: Automatic upgrade to secure connections
- **No Telemetry**: Zero data collection or reporting

## 📋 Requirements

- Python 3.7+
- PyQt5
- PyQtWebEngine
- PySocks (for Tor support)

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/Darkelf2024/Darkelf-Shadow.git
cd Darkelf-Shadow
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the browser:
```bash
python darkelf_shadow.py
```

## 🔧 Configuration

The browser includes a `config.json` file for customizing privacy settings:

- Enable/disable Tor routing
- Configure ad/tracker blocking rules
- Set custom user agents
- Adjust anti-fingerprinting measures

## 🌐 Tor Integration

To enable Tor routing:

1. Install Tor Browser or Tor service
2. Ensure Tor is running on default port (9050)
3. Enable Tor in the browser settings

## 🛡️ Privacy Features

### Anti-Fingerprinting
- Canvas fingerprinting protection
- WebGL fingerprinting protection
- Audio context fingerprinting protection
- Font fingerprinting protection
- Screen resolution spoofing

### Tracker Blocking
- Blocks known tracking domains
- Prevents third-party cookies
- Strips tracking parameters from URLs
- Blocks tracking pixels and beacons

### Ad Blocking
- Aggressive ad filtering
- Blocks pop-ups and pop-unders
- Prevents auto-playing media
- Filters sponsored content

## 📝 Usage

```bash
# Basic usage
python darkelf_shadow.py

# With custom homepage
python darkelf_shadow.py --homepage https://duckduckgo.com

# Enable Tor mode
python darkelf_shadow.py --tor

# Disable JavaScript (maximum security)
python darkelf_shadow.py --no-js
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## ⚖️ License

This project is open source and available under the MIT License.

## ⚠️ Disclaimer

This browser is designed for privacy and anonymity. Use responsibly and in accordance with all applicable laws. The developers are not responsible for any misuse of this software.

## 🔗 Links

- [GitHub Repository](https://github.com/Darkelf2024/Darkelf-Shadow)
- [Issue Tracker](https://github.com/Darkelf2024/Darkelf-Shadow/issues)

## 📊 Roadmap

- [ ] Enhanced Tor integration with circuit display
- [ ] Built-in VPN support
- [ ] Cryptocurrency payment blocking detection
- [ ] Advanced cookie management
- [ ] Profile isolation
- [ ] Encrypted bookmark storage
- [ ] Tab sandboxing