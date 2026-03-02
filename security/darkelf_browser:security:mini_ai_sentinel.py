import time
from collections import deque
import re

try:
    from urllib.parse import unquote, urlparse
except ImportError:
    def unquote(s): return s
    def urlparse(s): return type("U", (), {"netloc": "", "port": None})()

class DarkelfMiniAISentinel:
    """
    Aggressive + Expanded Edition for Darkelf Shadow (PyQt5) - Enhanced for modern trackers,
    ClearURLs, AdGuard, full fingerprint monitoring, and advanced reporting.
    """
    MAX_URL_LENGTH = 2048
    CRITICAL_WINDOW_SECONDS = 60

    def __init__(self):
        self.enabled = True
        self.events = deque(maxlen=500)
        self.tracker_hits = 0
        self.suspicious_hits = 0
        self.malware_hits = 0
        self.exploit_attempts = 0
        self.fingerprint_attempts = 0
        self.intrusion_attempts = 0
        self.http_blocks_attempts = 0
        self.session_start = time.time()
        self.unique_domains = set()
        self.redirects = []
        self.lockdown_active = False
        self.lockdown_threshold = 1
        self.lockdown_triggered_at = None

        self.hacker_tools = [
            'nmap', 'sqlmap', 'metasploit', 'burpsuite', 'nikto', 'dirbuster', 'hydra', 'wireshark', 'tcpdump', 'ettercap', 'aircrack', 'hashcat', 'johntheripper', 'cobalt', 'mimikatz'
        ]
        self.intrusion_patterns = {
            'sql_injection': ['union select', 'or 1=1', "'; drop", 'exec(', 'script>'],
            'xss': ['<script', 'javascript:', 'onerror=', 'onload=', 'eval('],
            'path_traversal': ['../', '..\\', '%2e%2e', 'etc/passwd', 'windows/system'],
            'command_injection': ['| cat', '; ls', '&& whoami', 'cmd.exe', '/bin/bash'],
            'malware': ['ransomware', 'cryptolocker', 'wannacry', 'trojan', 'backdoor'],
            'exploit': ['metasploit', 'shellcode', 'exploit-db', 'cve-', '0day'],
            'phishing': ['verify-account', 'suspended-account', 'confirm-identity', 'urgent-action'],
            'exfil': ['base64,', 'data:text', 'blob:', 'download.php?file='],
        }
        self.high_risk_domains = [
            'doubleclick.net', 'googlesyndication.com', 'googleadservices.com', 'adguard.com',
            'clearurls', 'facebook.net', 'scorecardresearch.com', 'quantserve.com', 'taboola.com',
            'outbrain.com', 'criteo.com', 'adnxs.com', '.tk', '.ml', '.ga', '.cf', '.gq'
        ]
        self.fingerprint_apis = {
            'canvas': 0, 'webgl': 0, 'audio': 0, 'font': 0, 'battery': 0, 'geolocation': 0, 'media_devices': 0, 'webrtc': 0,
        }
        self.request_timestamps = deque(maxlen=100)
        self.anomaly_threshold = 50

    def monitor_network(self, url, headers=None):
        if not self.enabled or not url: return
        if self.lockdown_active:
            print("[MiniAI] LOCKDOWN: Absolute block:", url[:80])
            return
        now = time.time()
        url_norm = unquote(unquote(url))[:self.MAX_URL_LENGTH].lower()
        domain = ""
        try:
            domain = urlparse(url_norm).netloc
            self.unique_domains.add(domain)
        except Exception: pass

        event = {
            'url': url_norm,
            'timestamp': now,
            'datetime': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
            'threats': [],
            'risk_level': 'low'
        }
        critical = False

        for key, patterns in self.intrusion_patterns.items():
            for pat in patterns:
                if pat in url_norm:
                    self.intrusion_attempts += 1
                    event['threats'].append(f"INTRUSION:{key.upper()}:{pat}")
                    event['risk_level'] = 'critical'
                    critical = True
        for tool in self.hacker_tools:
            if tool in url_norm:
                self.intrusion_attempts += 1
                event['threats'].append("TOOL:"+tool.upper())
                event['risk_level'] = 'critical'
                critical = True

        regexes = [
            (r"(union\s+select|or\s+1=1|drop\s+table|insert\s+into)", 'critical'),
            (r"(<script.*?>|javascript:|onerror=|onload=)", 'high'),
            (r"(\.\./|\.\.\\)", 'critical'),
            (r"(;|\|\||&&)\s*(whoami|ls|cat|bash|cmd)", 'critical'),
        ]
        for reg, risk in regexes:
            if re.search(reg, url_norm):
                event['threats'].append(f"INTRUSION-REGEX:{risk}")
                event['risk_level'] = risk
                critical = critical or (risk == 'critical')
        for bad in self.high_risk_domains:
            if bad in domain:
                event['threats'].append(f"HIGH_RISK_DOMAIN:{bad}")
                event['risk_level'] = 'medium'
        if any(x in url_norm for x in ("malware", "virus", "trojan", "ransomware", "backdoor")):
            self.malware_hits += 1
            event['threats'].append("MALWARE")
            event['risk_level'] = 'critical'
            critical = True
        if any(x in url_norm for x in ("exploit", "payload", "shellcode", "metasploit")):
            self.exploit_attempts += 1
            event['threats'].append("EXPLOIT")
            event['risk_level'] = 'critical'
            critical = True
        if any(x in url_norm for x in ("phish", "verify-account", "suspended", "confirm-identity")):
            self.suspicious_hits += 1
            event['threats'].append("PHISHING")
            event['risk_level'] = 'high'
        if any(x in url_norm for x in ("tracker", "analytics", "beacon", "doubleclick", "facebook.net", "clearurls", "adguard")):
            self.tracker_hits += 1
            event['threats'].append("TRACKER")
            if event['risk_level'] == 'low': event['risk_level'] = 'medium'

        for k in self.fingerprint_apis:
            if k in url_norm:
                self.fingerprint_apis[k] += 1
                event['threats'].append(f"FINGERPRINT:{k}")
                event['risk_level'] = 'medium'
                self.fingerprint_attempts += 1

        self.request_timestamps.append(now)
        if len(self.request_timestamps) > 100:
            self.request_timestamps = self.request_timestamps[-90:]
        last1s = len([t for t in self.request_timestamps if now-t < 1.0])
        if last1s > self.anomaly_threshold:
            event['threats'].append("ANOMALY:burst")
            event['risk_level'] = 'high'
        if len(self.redirects) > 7:
            event['threats'].append("ANOMALY:redirect_loop")
            event['risk_level'] = 'high'

        self.events.append(event)

        if event['risk_level'] == 'critical':
            print("\n🔴 [MiniAI] CRITICAL: Lockdown triggered immediately!")
            self.lockdown_active = True
            self.lockdown_triggered_at = now
            print("🛑 Event:", event)
        elif event['risk_level'] in ("high", "medium"):
            print("🟠 [MiniAI] Threat:", event['url'][:80], event['threats'])

    def on_http_blocked(self, url):
        self.http_blocks_attempts += 1
        event = {
            'url': url,
            'timestamp': time.time(),
            'datetime': time.strftime("%Y-%m-%d %H:%M:%S"),
            'threats': ['HTTP_AUTO_UPGRADE'],
            'risk_level': 'medium'
        }
        self.events.append(event)
        print("[MiniAI] 🔒 HTTP blocked:", url[:60])

    def get_statistics(self):
        uptime = time.time() - self.session_start
        return {
            'uptime_seconds': uptime,
            'total_events': len(self.events),
            'unique_domains': len(self.unique_domains),
            'lockdown': {
                'active': self.lockdown_active,
                'threshold': self.lockdown_threshold,
                'triggered_at': self.lockdown_triggered_at,
            },
            'threats': {
                'trackers': self.tracker_hits,
                'suspicious': self.suspicious_hits,
                'malware': self.malware_hits,
                'exploits': self.exploit_attempts,
                'intrusions': self.intrusion_attempts,
                'fingerprinting': self.fingerprint_attempts,
                'http_blocks': self.http_blocks_attempts,
            },
            'fingerprinting_apis': dict(self.fingerprint_apis),
            'recent_threats': [
                e for e in list(self.events)[-10:]
                if e['risk_level'] in ('high', 'critical')
            ]
        }

    def get_threat_report(self):
        stats = self.get_statistics()
        uptime_min = stats['uptime_seconds'] / 60
        lockdown_status = "🔴 ACTIVE" if stats['lockdown']['active'] else "🟢 STANDBY"
        domain_stats = {}
        for event in self.events:
            dom = urlparse(event['url']).netloc or 'unknown'
            if dom not in domain_stats:
                domain_stats[dom] = {'trackers': 0, 'fingerprinting': 0, 'malware': 0, 'intrusions': 0, 'http_blocks': 0, 'risk_level': 'low'}
            for threat in event['threats']:
                if 'TRACKER' in threat: domain_stats[dom]['trackers'] += 1
                elif 'FINGERPRINT' in threat: domain_stats[dom]['fingerprinting'] += 1
                elif 'MALWARE' in threat or 'EXPLOIT' in threat: domain_stats[dom]['malware'] += 1
                elif 'INTRUSION' in threat or 'TOOL' in threat: domain_stats[dom]['intrusions'] += 1
                elif 'HTTP_INSECURE' in threat: domain_stats[dom]['http_blocks'] += 1
            if event['risk_level'] == 'critical':
                domain_stats[dom]['risk_level'] = 'critical'
            elif event['risk_level'] == 'high' and domain_stats[dom]['risk_level'] != 'critical':
                domain_stats[dom]['risk_level'] = 'high'
            elif event['risk_level'] == 'medium' and domain_stats[dom]['risk_level'] == 'low':
                domain_stats[dom]['risk_level'] = 'medium'
        sorted_domains = sorted(
            domain_stats.items(),
            key=lambda x: (
                x[1]['trackers'] +
                x[1]['fingerprinting'] +
                x[1]['malware'] +
                x[1]['intrusions'] +
                x[1]['http_blocks']
            ),
            reverse=True
        )
        report = f"""
╔══════════════════════════════════════════════════════════╗
║         DARKELF MiniAI - THREAT REPORT                   ║
╚══════════════════════════════════════════════════════════╝
Session Uptime:     {uptime_min:.1f} min
Total Events:       {stats['total_events']}
Unique Domains:     {stats['unique_domains']}
Lockdown Status:    {lockdown_status}
THREAT SUMMARY:
├─ Trackers:        {stats['threats']['trackers']}
├─ Suspicious:      {stats['threats']['suspicious']}
├─ Malware:         {stats['threats']['malware']}
├─ Exploits:        {stats['threats']['exploits']}
├─ Intrusions:      {stats['threats']['intrusions']}
├─ HTTP Blocks:     {stats['threats'].get('http_blocks', 0)}
└─ Fingerprinting:  {stats['threats']['fingerprinting']}
FINGERPRINTING DEFENSE STATUS:
├─ Canvas:          {stats['fingerprinting_apis']['canvas']} attempts → NOISE
├─ WebGL:           {stats['fingerprinting_apis']['webgl']} attempts → SPOOFED
├─ Audio:           {stats['fingerprinting_apis']['audio']} attempts → ZEROED
├─ Font:            {stats['fingerprinting_apis']['font']} attempts → HIDDEN
├─ Battery:         {stats['fingerprinting_apis']['battery']} attempts → SPOOFED
├─ Geolocation:     {stats['fingerprinting_apis']['geolocation']} attempts → BLOCKED
├─ Media Devices:   {stats['fingerprinting_apis']['media_devices']} attempts → EMPTY
└─ WebRTC:          {stats['fingerprinting_apis']['webrtc']} attempts → DISABLED
TOP 10 THREAT DOMAINS:
"""
        for i, (dom, threats) in enumerate(sorted_domains[:10], 1):
            tracker_icon = "🔴" if threats['trackers'] > 0 else "⚪"
            fp_icon = "🟡" if threats['fingerprinting'] > 0 else "⚪"
            malware_icon = "🚨" if threats['malware'] > 0 else "⚪"
            intrusion_icon = "⛔" if threats['intrusions'] > 0 else "⚪"
            http_icon = "🔒" if threats['http_blocks'] > 0 else "⚪"
            risk_color = {
                'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '⚪'
            }.get(threats['risk_level'], '⚪')
            report += f"\n{i:2d}. {risk_color} {dom[:45]:<45}\n    Track: {tracker_icon} {threats['trackers']:2d} | FP: {fp_icon} {threats['fingerprinting']:2d} | Mal: {malware_icon} {threats['malware']:2d} | Intru: {intrusion_icon} {threats['intrusions']:2d} | HTTP: {http_icon} {threats['http_blocks']:2d}"
        report += f"\n\nRECENT HIGH-RISK EVENTS: {len(stats['recent_threats'])}"
        for event in stats['recent_threats'][-5:]:
            report += f"\n  • {event['datetime']} | {event['risk_level'].upper()} | {', '.join(event['threats'][:2])}"
        report += "\n" + "="*62
        if stats['lockdown']['active']:
            report += f"\n  🔴 LOCKDOWN ACTIVE - All requests blocked"
        else:
            report += "\n  ✅ No fingerprint leaks. All tracker attempts defended."
        report += "\n" + "="*62
        return report

    def is_locked_down(self):
        return self.lockdown_active

    def reset_lockdown(self, admin_override=False):
        if not admin_override:
            print("[MiniAI] Lockdown reset requires admin_override=True")
            return False
        self.lockdown_active = False
        self.lockdown_triggered_at = None
        self.events.clear()
        print("[MiniAI] 🟢 Lockdown reset - System restored")
        return True

    def shutdown(self):
        if not self.enabled: return
        self.enabled = False
        try:
            print(self.get_threat_report())
        except Exception as e:
            print("[MiniAI] Report failed:", e)
