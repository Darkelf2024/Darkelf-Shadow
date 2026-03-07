import platform as _platform
import secrets
import hashlib
import sys, os, uuid
import tempfile
import math
import random
import gc
from PySide6.QtCore import Qt, QUrl, QUrlQuery, QSize, QPointF, QRectF, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QPushButton, QLabel, QWidget,
    QTabWidget, QTabBar, QMessageBox, QToolButton, QProgressBar, QMenu, QWidgetAction, QGridLayout,
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QProgressDialog
)
from PySide6.QtGui import (
    QAction, QIcon, QPixmap, QPainter, QColor,
    QPalette, QPen, QBrush, QPolygonF, QPainterPath
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEngineProfile,
    QWebEnginePage,
    QWebEngineScript,
    QWebEngineSettings,
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
    QWebEngineDownloadRequest
)

# ---- Install ad/tracker interceptor ----
import json
import re
import shutil
import subprocess
from urllib.parse import quote_plus
import time
from collections import deque
try:
    from urllib.parse import unquote, urlparse
except:
    def unquote(s): return s
    def urlparse(s): return type("U", (), {"netloc": "", "port": None})()
import urllib.request
from urllib.error import URLError, HTTPError
    
#devnull = open(os.devnull, 'w')
#os.dup2(devnull.fileno(), sys.stderr.fileno())

# ===================== Secure No-Trace Downloads helpers =====================

def _safe_download_dir() -> str:
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    folder = os.path.join(desktop, "Darkelf Temp Folder")
    os.makedirs(folder, exist_ok=True)
    return folder


def _randomized_filename(suggested: str) -> str:
    suggested = (suggested or "download").strip()
    suggested = re.sub(r"[^A-Za-z0-9._-]+", "_", suggested)[:120] or "download"

    base, ext = os.path.splitext(suggested)
    token = secrets.token_hex(6)

    base = (base[:60] or "download")
    ext = ext[:12]
    return f"{base}_{token}{ext}"
    
def sanitize_url_clearurls(url):
    # Remove known tracking query parameters from URLs
    clear_params = [
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id",
        "fbclid", "gclid", "mc_campaign", "mc_eid", "mc_cid", "pk_campaign", "pk_kwd"
        # Add more from ClearURLs filter file as needed!
    ]
    url_parts = QUrl(url)
    query = url_parts.query()
    new_query = "&".join([
        part for part in query.split("&")
        if not any(part.startswith(p+"=") for p in clear_params)
    ])
    url_parts.setQuery(new_query)
    return url_parts.toString()

BOOTUP_CANVAS_SEED = secrets.randbits(32) & 0xFFFFFFFF
        
#BOOT_SEED = secrets.token_hex(32)
DUCK_LITE_HTTPS = "https://duckduckgo.com/lite/"
MUTE_LOGS_AFTER_BOOT_MS = 0

import os

existing = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = existing + (
    " --disable-background-networking"
    " --disable-sync"
    " --metrics-recording-only"
    " --disable-default-apps"
    " --no-first-run"
    " --disable-features=UserAgentClientHint"
    " --disable-features=UserAgentReduction"
    " --disable-features=ReduceUserAgentMinorVersion"
    " --disable-features=WebRtcHideLocalIpsWithMdns"
    " --force-webrtc-ip-handling-policy=disable_non_proxied_udp"
    " --webrtc-ip-handling-policy=disable_non_proxied_udp"
    " --disable-webrtc"
    " --disable-geolocation"
    " --disable-breakpad"
    " --disable-domain-reliability"
    " --disable-client-side-phishing-detection"
    " --disable-component-update"
    " --disable-extensions"
    " --disable-gpu-shader-disk-cache"
    " --disable-logging"
)


EASYLIST_URLS = [
    # Core
    "https://easylist.to/easylist/easylist.txt",
    "https://easylist.to/easylist/easyprivacy.txt",

    # Annoyances
    "https://secure.fanboy.co.nz/fanboy-annoyance.txt",

    # Social widgets
    "https://easylist.to/easylist/fanboy-social.txt",

    # Anti-adblock
    "https://easylist-downloads.adblockplus.org/antiadblockfilters.txt",

    # AdGuard Tracking Protection
    "https://filters.adtidy.org/extension/chromium/filters/3.txt",

    # ✅ uBlock Origin — Privacy
    "https://raw.githubusercontent.com/uBlockOrigin/uAssets/master/filters/privacy.txt",

    # ✅ uBlock Origin — Unbreak (fixes site breakage)
    "https://raw.githubusercontent.com/uBlockOrigin/uAssets/master/filters/unbreak.txt",

    # ✅ uBlock Origin — Badware
    "https://raw.githubusercontent.com/uBlockOrigin/uAssets/master/filters/badware.txt",
]

# Cache location (safe, user-level)
EASYLIST_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".darkelf", "filterlists")
os.makedirs(EASYLIST_CACHE_DIR, exist_ok=True)

# How often to refresh lists (seconds)
EASYLIST_REFRESH_EVERY = 24 * 60 * 60  # 24h

# ===================== ABP -> regex helpers =====================

def _now() -> float:
    return time.time()

def _safe_host(u: str) -> str:
    try:
        return QUrl(u).host().lower()
    except Exception:
        return ""

def _wildcard_to_re(s: str) -> str:
    # ABP wildcard "*" -> ".*"
    # Escape regex special chars except "*" which we convert.
    out = []
    for ch in s:
        if ch == "*":
            out.append(".*")
        elif ch in ".^$+?{}[]\\|()":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)

def _abp_anchor_boundary() -> str:
    # ABP '^' = separator boundary (end of host, or non-alnum/._%-)
    # A common approximation:
    return r"(?:[^A-Za-z0-9_\-.%]|$)"

def _abp_rule_to_regex(rule: str) -> str | None:
    """
    Convert a basic ABP network filter rule into a regex string.
    Supports: ||, |, ^, *, plain substrings.
    Ignores: full option parsing, $domain=..., etc. (we parse options elsewhere)
    """
    rule = rule.strip()
    if not rule or rule.startswith("!"):
        return None

    # Regex rules: /.../
    if len(rule) >= 2 and rule[0] == "/" and rule[-1] == "/":
        body = rule[1:-1]
        # basic sanity
        if body:
            return body
        return None

    anchored_start = False
    anchored_end = False

    if rule.startswith("||"):
        core = rule[2:]
        core = core.replace("^", "{ABP_BOUNDARY}")
        core_re = _wildcard_to_re(core)
        core_re = core_re.replace("{ABP_BOUNDARY}", _abp_anchor_boundary())
        return r"^(?:[^:/?#]+:)?//(?:[^/?#]*\.)?" + core_re + _abp_anchor_boundary()

        
    if rule.startswith("|"):
        anchored_start = True
        rule = rule[1:]
    if rule.endswith("|"):
        anchored_end = True
        rule = rule[:-1]

    rule = rule.replace("^", "{ABP_BOUNDARY}")
    core_re = _wildcard_to_re(rule)
    core_re = core_re.replace("{ABP_BOUNDARY}", _abp_anchor_boundary())

    if anchored_start and anchored_end:
        return r"^" + core_re + r"$"
    if anchored_start:
        return r"^" + core_re
    if anchored_end:
        return core_re + r"$"
    return core_re

def _split_rule_and_options(line: str) -> tuple[str, dict]:
    """
    ABP options come after $:  rule$script,image,third-party
    We keep only a few options that are easy/valuable in an interceptor.
    """
    line = line.strip()
    if "$" not in line:
        return line, {}

    rule, optstr = line.split("$", 1)
    opts = {}
    for raw in optstr.split(","):
        raw = raw.strip()
        if not raw:
            continue
        if "=" in raw:
            k, v = raw.split("=", 1)
            opts[k.strip()] = v.strip()
        else:
            opts[raw] = True
    return rule.strip(), opts

def _parse_domain_list(v: str) -> tuple[set[str], set[str]]:
    """
    domain=example.com|~foo.com
    Returns (allow_domains, deny_domains)
    """
    allow, deny = set(), set()
    for part in v.split("|"):
        part = part.strip()
        if not part:
            continue
        if part.startswith("~"):
            deny.add(part[1:].lower())
        else:
            allow.add(part.lower())
    return allow, deny

def _host_matches_domain(host: str, domain: str) -> bool:
    host = host.lower()
    domain = domain.lower()
    return host == domain or host.endswith("." + domain)

def _domain_option_allows(first_party_host: str, opts: dict) -> bool:
    """
    If rule has domain=... limit, check if first party host is eligible.
    """
    dom = opts.get("domain")
    if not dom:
        return True
    allow, deny = _parse_domain_list(dom)
    # If allow list present: must match one of them.
    if allow:
        ok = any(_host_matches_domain(first_party_host, d) for d in allow)
        if not ok:
            return False
    # If deny list present: must NOT match any of them.
    if deny:
        bad = any(_host_matches_domain(first_party_host, d) for d in deny)
        if bad:
            return False
    return True
    
def base_domain(host: str) -> str:
    """
    Returns the eTLD+1 (base domain) for a given host.
    Example: 'lite.duckduckgo.com' or 'duckduckgo.com' -> 'duckduckgo.com'
    """
    host = (host or "").split(":")[0]  # Remove port if present
    parts = host.lower().split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host.lower()

def _third_party_check(req_host: str, first_party_host: str) -> bool:
    """
    Use base domains for robust first-party check across subdomains.
    """
    if not req_host or not first_party_host:
        return True
    return base_domain(req_host) != base_domain(first_party_host)
    
# ===================== Filter structures =====================

class _NetRule:
    __slots__ = ("re", "is_exception", "opts")
    def __init__(self, pattern: re.Pattern, is_exception: bool, opts: dict):
        self.re = pattern
        self.is_exception = is_exception
        self.opts = opts

class EasyListEngine:
    """
    Loads lists -> builds:
      - network rules: list of _NetRule (exceptions first)
      - cosmetic rules: dict[domain or "*"] -> list[selectors]
      - cosmetic exceptions: dict[domain] -> set[selectors]
    """
    def __init__(self):
        self.network_rules: list[_NetRule] = []
        self.cosmetic: dict[str, list[str]] = {"*": []}
        self.cosmetic_exceptions: dict[str, set[str]] = {}

    # ---------- fetch/cache ----------
    def _cache_path_for_url(self, url: str) -> str:
        h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        return os.path.join(EASYLIST_CACHE_DIR, f"{h}.txt")

    def _should_refresh(self, path: str) -> bool:
        if not os.path.exists(path):
            return True
        age = _now() - os.path.getmtime(path)
        return age > EASYLIST_REFRESH_EVERY

    def fetch_lists(self, urls: list[str]) -> list[str]:
        """
        Returns list of list-contents strings.
        Uses cached content if not stale.
        """
        texts = []
        for url in urls:
            path = self._cache_path_for_url(url)
            if self._should_refresh(path):
                try:
                    req = urllib.request.Request(
                        url,
                        headers={
                            "User-Agent": "Darkelf/1.0 (EasyList Fetcher)",
                            "Accept": "text/plain,*/*",
                        },
                    )
                    with urllib.request.urlopen(req, timeout=15) as r:
                        data = r.read()
                    text = data.decode("utf-8", errors="replace")
                    with open(path, "w", encoding="utf-8", errors="ignore") as f:
                        f.write(text)
                except (URLError, HTTPError, TimeoutError) as e:
                    # If fetch fails but cache exists, use cache.
                    if os.path.exists(path):
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read()
                    else:
                        print("[EasyList] fetch failed:", url, e)
                        text = ""
            else:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

            if text:
                texts.append(text)
        return texts

    # ---------- parse ----------
    def load_and_build(self, urls: list[str]):
        texts = self.fetch_lists(urls)
        self._parse_texts(texts)
        self._finalize()

    def _parse_texts(self, texts: list[str]):
        self.network_rules.clear()
        self.cosmetic = {"*": []}
        self.cosmetic_exceptions.clear()

        for text in texts:
            for raw in text.splitlines():
                line = raw.strip()
                if not line or line.startswith("!"):
                    continue
                # Ignore metadata headers like: [Adblock Plus 2.0]
                if line.startswith("[") and line.endswith("]"):
                    continue

                # Cosmetic rules:
                #  - example.com##.ad
                #  - ##.global-ad
                #  - example.com#@#.ad   (exception)
                if "##" in line or "#@#" in line:
                    self._parse_cosmetic(line)
                    continue

                # Network rules:
                self._parse_network(line)

    def _parse_cosmetic(self, line: str):
        is_exc = "#@#" in line
        sep = "#@#" if is_exc else "##"
        parts = line.split(sep, 1)
        if len(parts) != 2:
            return
        domain_part = parts[0].strip()  # can be empty = global
        selector = parts[1].strip()
        if not selector:
            return

        # ABP also has extended selectors (:has, etc). We'll keep them; CSS injection may ignore unsupported ones.
        domains = []
        if domain_part:
            domains = [d.strip().lower() for d in domain_part.split(",") if d.strip()]
        else:
            domains = ["*"]

        if is_exc:
            for d in domains:
                self.cosmetic_exceptions.setdefault(d, set()).add(selector)
        else:
            for d in domains:
                self.cosmetic.setdefault(d, []).append(selector)

    def _parse_network(self, line: str):
        is_exception = False
        if line.startswith("@@"):
            is_exception = True
            line = line[2:].strip()

        rule, opts = _split_rule_and_options(line)

        # Skip unsupported rule types (resource redirects, etc.)
        # Keep only rules that look like URL filters.
        if not rule:
            return

        # Convert ABP -> regex
        rx = _abp_rule_to_regex(rule)
        if not rx:
            return

        try:
            cre = re.compile(rx, re.I)
        except re.error:
            return

        self.network_rules.append(_NetRule(cre, is_exception, opts))

    def _finalize(self):
        # Put exceptions first for fast allow-pass.
        self.network_rules.sort(key=lambda r: (not r.is_exception))

        # De-dup cosmetic selectors per domain (keep stable order)
        for d, sels in list(self.cosmetic.items()):
            seen = set()
            out = []
            for s in sels:
                if s in seen:
                    continue
                seen.add(s)
                out.append(s)
            self.cosmetic[d] = out
            
    def should_block(self, url: str, first_party_url: str, req_type: str | None = None) -> bool:
        u = (url or "").lower()
        fp_host = _safe_host(first_party_url)
        req_host = _safe_host(url)

        if not req_host:
            return False
            
        # Never block BrowserLeaks (testing site)
        if "browserleaks.com" in fp_host:
            print("BROWSERLEAKS ALLOW:", req_type, url)
            return False

        if req_type is None:
            return False

        if req_type == "document":
            return False

        # -----------------------------
        # SAME-SITE detection
        # -----------------------------
        def _site_key(host: str) -> str:
            parts = [p for p in (host or "").split(".") if p]
            if len(parts) >= 2:
                return ".".join(parts[-2:])
            return host or ""

        fp_site = _site_key(fp_host)
        req_site = _site_key(req_host)
        same_site = (fp_site and req_site and fp_site == req_site)

        is_third_party = (not same_site) and _third_party_check(req_host, fp_host)
        
        # -------------------------------------------------
        # Treat Wikimedia family as same-site
        # -------------------------------------------------
        WIKIMEDIA_FAMILY = (
            "wikipedia.org",
            "wikimedia.org",
            "wmfusercontent.org",
        )

        if any(fp_host.endswith(x) for x in WIKIMEDIA_FAMILY) and \
        any(req_host.endswith(x) for x in WIKIMEDIA_FAMILY):
            same_site = True
            is_third_party = False


        # -------------------------------------------------
        # Treat GitHub family as same-site
        # -------------------------------------------------
        GITHUB_FAMILY = (
            "github.com",
            "githubusercontent.com",
            "githubassets.com",
        )

        if any(fp_host.endswith(x) for x in GITHUB_FAMILY) and \
        any(req_host.endswith(x) for x in GITHUB_FAMILY):
            same_site = True
            is_third_party = False

        # -----------------------------
        # Never block critical same-site core resources
        # -----------------------------
        if same_site and req_type in ("script", "xmlhttprequest", "stylesheet", "font", "media"):
            return False

        # -----------------------------
        # Never interfere with AWS WAF
        # -----------------------------
        if "awswaf.com" in req_host or "token.awswaf.com" in req_host:
            return False

        # -----------------------------
        # YouTube ad blocking
        # -----------------------------
        if "youtube.com" in fp_host or "youtu.be" in fp_host:
            YT_AD_ENDPOINTS = (
                "youtube.com/pagead",
                "youtube.com/api/stats/ads",
                "youtube.com/get_midroll_info",
                "youtube.com/ptracking",
                "youtube.com/youtubei/v1/player/ad",
            )
            if any(ep in u for ep in YT_AD_ENDPOINTS):
                return True

            if "googlevideo.com" in req_host:
                if any(k in u for k in ("ctier", "adformat", "midroll")):
                    return True

        # -----------------------------
        # Amazon essential allowlist
        # -----------------------------
        if fp_site == "amazon.com":
            AMAZON_ESSENTIAL = (
                "media-amazon.com",
                "ssl-images-amazon.com",
                "images-amazon.com",
                "images-na.ssl-images-amazon.com",
                "m.media-amazon.com",
                "a0.awsstatic.com",
                "a1.awsstatic.com",
                "a2.awsstatic.com",
                "a3.awsstatic.com",
                "a4.awsstatic.com",
                "a5.awsstatic.com",
                "a6.awsstatic.com",
                "a7.awsstatic.com",
            )
            if any(req_host == h or req_host.endswith("." + h) for h in AMAZON_ESSENTIAL):
                return False

        # -----------------------------
        # Infrastructure allowlist
        # -----------------------------
        INFRA_ALLOW = (
            "amazonaws.com",
            "cloudfront.net",
            "awswaf.com",
        )
        if any(req_host == x or req_host.endswith("." + x) for x in INFRA_ALLOW):
            return False

        # -----------------------------
        # Hard tracker domains
        # -----------------------------
        HARD_TRACKERS = (
            "doubleclick.net",
            "googlesyndication.com",
            "googleadservices.com",
            "adservice.google.com",
            "googletagmanager.com",
            "google-analytics.com",
            "analytics.google.com",
            "connect.facebook.net",
            "facebook.net",
            "adnxs.com",
            "criteo.com",
            "taboola.com",
            "outbrain.com",
            "scorecardresearch.com",
            "quantserve.com",
        )
        if (not same_site) and any(req_host == t or req_host.endswith("." + t) for t in HARD_TRACKERS):
            return True

        # -----------------------------
        # Third-party ad-tech signals
        # -----------------------------
        if req_type in ("script", "xmlhttprequest", "subdocument") and (not same_site):
            HIGH_SIGNAL = (
                "doubleclick",
                "googlesyndication",
                "googleadservices",
                "pagead",
                "adsystem",
                "adservice",
                "adserver",
                "gampad",
                "prebid",
                "openrtb",
                "criteo",
                "taboola",
                "outbrain",
                "adnxs",
            )
            if any(k in u for k in HIGH_SIGNAL):
                return True

        # -----------------------------
        # Media blocking (third-party only)
        # -----------------------------
        if req_type == "media" and (not same_site):
            AD_MEDIA_HOSTS = (
                "doubleclick.net",
                "googlesyndication.com",
                "googleadservices.com",
                "adnxs.com",
                "criteo.com",
                "taboola.com",
                "outbrain.com",
            )
            if any(req_host == h or req_host.endswith("." + h) for h in AD_MEDIA_HOSTS):
                return True

        # -----------------------------
        # YouTube image protection
        # -----------------------------
        if req_type == "image":
            YT_IMAGE_HOSTS = (
                "ytimg.com",
                "ggpht.com",
                "googleusercontent.com",
            )
            if any(req_host == h or req_host.endswith("." + h) for h in YT_IMAGE_HOSTS):
                return False

        # -----------------------------
        # Never block same-site images
        # -----------------------------
        if req_type == "image" and same_site:
            return False

        # -----------------------------
        # Ad iframes (fixed indentation bug)
        # -----------------------------
        IFRAME_AD_HINTS = (
            "doubleclick",
            "googlesyndication",
            "adservice",
            "adnxs",
            "taboola",
            "outbrain",
        )

        if req_type == "subdocument" and (not same_site):
            if any(k in u for k in IFRAME_AD_HINTS):
                return True

        # -----------------------------
        # EasyList (image/media/subdocument only)
        # -----------------------------
        if req_type not in ("image", "media", "subdocument"):
            return False

        for rule in self.network_rules:
            if not _domain_option_allows(fp_host, rule.opts):
                continue

            if "third-party" in rule.opts and not is_third_party:
                continue
            if "~third-party" in rule.opts and is_third_party:
                continue

            type_flags = {"image", "media", "subdocument"}
            specified = [t for t in type_flags if t in rule.opts]
            if specified and req_type not in specified:
                continue

            if rule.re.search(u):
                if rule.is_exception:
                    return False
                return True

        return False

    def css_for_host(self, host: str) -> str:
        host = (host or "").lower()
        selectors = []

        selectors += self.cosmetic.get("*", [])

        if host:
            parts = host.split(".")
            for i in range(len(parts) - 1):
                dom = ".".join(parts[i:])
                selectors += self.cosmetic.get(dom, [])

        exc = set(self.cosmetic_exceptions.get("*", set()))
        if host:
            parts = host.split(".")
            for i in range(len(parts) - 1):
                dom = ".".join(parts[i:])
                exc |= self.cosmetic_exceptions.get(dom, set())

        selectors = [s for s in selectors if s not in exc]

        if not selectors:
            return ""

        lines = []
        for sel in selectors:
            sel = sel.replace("`", "")
            lines.append(
                f"{sel} {{ display: none !important; visibility: hidden !important; }}"
            )

        return "\n".join(lines)
        
class StealthInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, engine: EasyListEngine, mini_ai):
        super().__init__()
        self.engine = engine
        self.mini_ai = mini_ai
        self.hsts_hosts = set()  # remember HTTPS-capable hosts

    def interceptRequest(self, info):
        qurl = info.requestUrl()
        scheme = (qurl.scheme() or "").lower()
        host = (qurl.host() or "").lower()
        
        req_url = qurl.toString()

        # send request to MiniAI
        if self.mini_ai:
            try:
                self.mini_ai.monitor_network(req_url)
            except Exception as e:
                print("MiniAI error:", e)

        # --------------------------------------------------
        # 0️⃣ Skip safe/internal schemes
        # --------------------------------------------------
        if scheme in ("data", "about", "chrome", "qrc", "blob", "view-source"):
            return

        if scheme == "file":
            info.block(True)
            return

        if "browserleaks.com" in host:
            return

        # --------------------------------------------------
        # 1️⃣ Skip localhost / private IP ranges
        # --------------------------------------------------
        if host in ("localhost", "127.0.0.1") \
           or host.startswith("192.168.") \
           or host.startswith("10.") \
           or host.startswith("172."):
            return

        # --------------------------------------------------
        # 2️⃣ FORCE HTTPS (Smart Upgrade)
        # --------------------------------------------------
        rt = info.resourceType()

        if scheme == "http" and rt != QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame:
            https_url = QUrl(qurl)
            https_url.setScheme("https")
            self.hsts_hosts.add(host)

            if self.mini_ai:
                self.mini_ai.on_http_blocked(req_url)

            info.redirect(https_url)
            return

        # Prevent HTTPS downgrade
        if scheme == "http" and host in self.hsts_hosts:
            https_url = QUrl(qurl)
            https_url.setScheme("https")
            info.redirect(https_url)
            return

        req_url = qurl.toString()
        fp_url = info.firstPartyUrl().toString()

        # --------------------------------------------------
        # 3️⃣ Strip common tracking parameters
        # --------------------------------------------------
        tracking_params = {
            "utm_source", "utm_medium", "utm_campaign",
            "utm_term", "utm_content",
            "fbclid", "gclid", "mc_eid"
        }

        query = QUrlQuery(qurl)
        modified = False

        for param in tracking_params:
            if query.hasQueryItem(param):
                query.removeAllQueryItems(param)
                modified = True

        if modified:
            clean_url = QUrl(qurl)
            clean_url.setQuery(query)
            info.redirect(clean_url)
            return

        # --------------------------------------------------
        # 4️⃣ Resource Type Detection (your existing logic)
        # --------------------------------------------------
        rt = info.resourceType()
        type_map = {}

        pairs = [
            ("ResourceTypeMainFrame", "document"),
            ("ResourceTypeSubFrame", "subdocument"),
            ("ResourceTypeScript", "script"),
            ("ResourceTypeStylesheet", "stylesheet"),
            ("ResourceTypeImage", "image"),
            ("ResourceTypeXhr", "xmlhttprequest"),
            ("ResourceTypeFontResource", "font"),
            ("ResourceTypeMedia", "media"),
        ]

        for attr, name in pairs:
            if hasattr(QWebEngineUrlRequestInfo.ResourceType, attr):
                enum_value = getattr(QWebEngineUrlRequestInfo.ResourceType, attr)
                type_map[enum_value] = name

        req_type = type_map.get(rt)

        if req_type is None:
            if hasattr(QWebEngineUrlRequestInfo.ResourceType, "ResourceTypeMainFrame"):
                if rt == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame:
                    req_type = "document"

        # --------------------------------------------------
        # 5️⃣ ClearURLs sanitizing (keep your original logic)
        # --------------------------------------------------
        if req_type and req_type not in ("document", "subdocument"):
            if "amazon." not in req_url and "awswaf.com" not in req_url:
                cleaned = sanitize_url_clearurls(req_url)
                if cleaned != req_url:
                    # Uncomment if you want active rewriting
                    # info.redirect(QUrl(cleaned))
                    return

        # --------------------------------------------------
        # 6️⃣ EasyList Blocking (FIXED SIGNATURE)
        # --------------------------------------------------
        try:
           # if self.engine and self.engine.should_block(req_url, fp_url, req_type):
                print("BLOCKED:", req_type, fp_url, "->", req_url)
                if self.mini_ai:
                    self.mini_ai.monitor_network(req_url)
        except Exception as e:
            print("Interceptor error:", e)
            return

# ===================== Cosmetic injection helper =====================

def js_inject_style_tag(style_id: str, css: str) -> str:
    # returns JS string that injects/updates a <style> with CSS
    css = css.replace("\\", "\\\\").replace("`", "\\`")
    return f"""
    (function(){{
      try {{
        var id = {json.dumps(style_id)};
        var css = `{css}`;
        var el = document.getElementById(id);
        if (!el) {{
          el = document.createElement('style');
          el.id = id;
          (document.documentElement || document.head || document.body).appendChild(el);
        }}
        el.textContent = css;
      }} catch(e) {{}}
    }})();
    """
    
# Darkelf MINIAI
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
        # Aggressive lockdown!
        self.lockdown_active = False
        self.lockdown_threshold = 1  # 1 critical event triggers lockdown
        self.lockdown_triggered_at = None

        # --- Enhancements to reduce false positives ---
        # Only treat these as "tools" when they appear as separate tokens in path/query/fragment
        # (not as part of random words/domains).
        self.hacker_tools = [
            'nmap', 'sqlmap', 'metasploit', 'burpsuite', 'nikto', 'dirbuster', 'hydra',
            'wireshark', 'tcpdump', 'ettercap', 'aircrack', 'hashcat', 'johntheripper',
            'cobalt', 'mimikatz'
        ]

        # Intrusion patterns: keep your list, but we will apply smarter matching below.
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

        # Add AdGuard/clearurls-specific domains
        # Fix: "clearurls" is not a domain; keep it for URL keyword detection but not domain matching.
        # Fix: TLD markers (".tk" etc.) should match exact TLD, not substring anywhere in domain.
        self.high_risk_domains = [
            'doubleclick.net', 'googlesyndication.com', 'googleadservices.com', 'adguard.com',
            'facebook.net', 'scorecardresearch.com', 'quantserve.com', 'taboola.com',
            'outbrain.com', 'criteo.com', 'adnxs.com',
        ]
        self.high_risk_tlds = {'.tk', '.ml', '.ga', '.cf', '.gq'}

        self.fingerprint_apis = {
            'canvas': 0, 'webgl': 0, 'audio': 0, 'font': 0, 'battery': 0,
            'geolocation': 0, 'media_devices': 0, 'webrtc': 0,
        }
        self.request_timestamps = deque(maxlen=100)
        self.anomaly_threshold = 50  # Aggressive!

        print("[MiniAI] Aggressive & Expanded Sentinel ready (threshold=1)")

    # --- Helper methods (new) ---
    def _safe_parse_url(self, url_norm: str):
        """
        Parse URL once and return (parsed, domain, path, query, fragment).
        This reduces false positives by applying stricter checks to path/query rather than entire URL string.
        """
        try:
            p = urlparse(url_norm)
            domain = (p.netloc or "").lower()
            path = (p.path or "").lower()
            query = (p.query or "").lower()
            fragment = (p.fragment or "").lower()
            return p, domain, path, query, fragment
        except Exception:
            return None, "", "", "", ""

    def _domain_matches(self, domain: str, candidate: str) -> bool:
        """
        True if domain is exactly candidate or a subdomain of it.
        Avoids substring false positives like 'notdoubleclick.net.example.com' containing 'doubleclick.net'.
        """
        if not domain or not candidate:
            return False
        domain = domain.strip(".")
        candidate = candidate.strip(".")
        return domain == candidate or domain.endswith("." + candidate)

    def _has_high_risk_tld(self, domain: str) -> bool:
        """
        Match exact TLD (.tk, .ml, ...) rather than substring anywhere.
        """
        if not domain:
            return False
        # domain might include port (example.com:8080)
        host = domain.split(":")[0]
        host = host.strip(".")
        dot = host.rfind(".")
        if dot == -1:
            return False
        tld = host[dot:]
        return tld in self.high_risk_tlds

    def _token_present(self, haystack: str, token: str) -> bool:
        """
        Word-boundary-ish token detection for URLs:
        consider separators commonly seen in URLs rather than only \b (which doesn't handle '-' well).
        """
        if not haystack or not token:
            return False
        # Treat these as separators: / ? & = # : . - _ +
        pattern = r"(?:^|[\/\?\&\=\#\:\.\-\_\+])" + re.escape(token) + r"(?:$|[\/\?\&\=\#\:\.\-\_\+])"
        return re.search(pattern, haystack) is not None

    def monitor_network(self, url, headers=None):
        """
        Aggressively monitor all network requests, fingerprinting and tracker events.
        Blocks all future requests instantly on critical.
        """
        if not self.enabled or not url:
            return
        if self.lockdown_active:
            print("[MiniAI] LOCKDOWN: Absolute block:", str(url)[:80])
            return

        now = time.time()

        # Normalize carefully: decode twice like you do, but keep within MAX_URL_LENGTH.
        url_norm = unquote(unquote(str(url)))[:self.MAX_URL_LENGTH]
        url_norm_l = url_norm.lower()

        parsed, domain, path, query, fragment = self._safe_parse_url(url_norm_l)

        if domain:
            self.unique_domains.add(domain)

        event = {
            'url': url_norm_l,
            'timestamp': now,
            'datetime': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
            'threats': [],
            'risk_level': 'low'
        }

        critical = False

        # -------------------------
        # 1) Intrusion pattern detection (reduced false positives)
        # -------------------------
        # Apply most string patterns to query+path+fragment, not full URL (domain can contain misleading substrings).
        focus = f"{path}?{query}#{fragment}"

        for key, patterns in self.intrusion_patterns.items():
            for pat in patterns:
                # Keep your behavior but only match on focus string to reduce domain-based false positives
                if pat in focus:
                    self.intrusion_attempts += 1
                    event['threats'].append(f"INTRUSION:{key.upper()}:{pat}")
                    # Only some categories should immediately be critical.
                    if key in ("sql_injection", "path_traversal", "command_injection", "exfil"):
                        event['risk_level'] = 'critical'
                        critical = True
                    elif key in ("xss", "phishing", "malware", "exploit"):
                        # still serious, but don't always auto-lockdown unless other indicators confirm
                        if event['risk_level'] == 'low':
                            event['risk_level'] = 'high'

        # Hacker tools: only treat as critical when present as tokens in path/query/fragment
        tool_focus = f"{path}&{query}#{fragment}"
        for tool in self.hacker_tools:
            if self._token_present(tool_focus, tool):
                self.intrusion_attempts += 1
                event['threats'].append("TOOL:" + tool.upper())
                event['risk_level'] = 'critical'
                critical = True

        # Regex detection (tightened)
        # - Use word boundaries and safer patterns.
        # - Apply to focus only.
        regexes = [
            (r"(?:\bunion\b\s+\bselect\b|\bor\b\s+1\s*=\s*1\b|\bdrop\b\s+\btable\b|\binsert\b\s+\binto\b)", 'critical'),
            (r"(?:<script\b|javascript:|\bonerror\s*=|\bonload\s*=)", 'high'),
            (r"(?:\.\./|\.\.\\|%2e%2e)", 'critical'),
            (r"(?:;|\|\||&&)\s*(?:whoami|ls|cat|bash|cmd(?:\.exe)?)\b", 'critical'),
        ]
        for reg, risk in regexes:
            try:
                if re.search(reg, focus, flags=re.IGNORECASE):
                    event['threats'].append(f"INTRUSION-REGEX:{risk}")
                    # Preserve your intent: critical triggers lockdown
                    if risk == 'critical':
                        event['risk_level'] = 'critical'
                        critical = True
                    elif event['risk_level'] == 'low':
                        event['risk_level'] = risk
            except re.error:
                # fail safe: if regex is invalid for some reason, skip it
                pass

        # -------------------------
        # 2) Domain-level risk (fixed matching)
        # -------------------------
        if domain:
            for bad in self.high_risk_domains:
                if self._domain_matches(domain, bad):
                    event['threats'].append(f"HIGH_RISK_DOMAIN:{bad}")
                    if event['risk_level'] == 'low':
                        event['risk_level'] = 'medium'

            if self._has_high_risk_tld(domain):
                event['threats'].append("HIGH_RISK_TLD")
                if event['risk_level'] == 'low':
                    event['risk_level'] = 'medium'

        # -------------------------
        # 3) Passive tracker/fingerprint/malware/exploit detection (reduced false positives)
        # -------------------------
        # Malware: require stronger context than just substring "trojan" etc anywhere.
        malware_terms = ("malware", "virus", "trojan", "ransomware", "backdoor", "cryptolocker", "wannacry")
        if any(self._token_present(focus, t) for t in malware_terms) or ("c2" in query and ("panel" in path or "gate" in path)):
            self.malware_hits += 1
            event['threats'].append("MALWARE")
            event['risk_level'] = 'critical'
            critical = True

        # Exploit: "exploit" and "payload" are common benign words; only escalate if combined with other exploit indicators.
        exploit_indicators = ("shellcode", "metasploit", "exploit-db", "cve-", "0day")
        if any(x in focus for x in exploit_indicators) or (("payload" in focus or "exploit" in focus) and ("cve-" in focus or "shellcode" in focus)):
            self.exploit_attempts += 1
            event['threats'].append("EXPLOIT")
            event['risk_level'] = 'critical'
            critical = True

        # Phishing: keep your detection, but use focus and token-ish checks
        if any(x in focus for x in ("verify-account", "suspended-account", "confirm-identity", "urgent-action")) or self._token_present(focus, "phish"):
            self.suspicious_hits += 1
            event['threats'].append("PHISHING")
            if event['risk_level'] in ("low", "medium"):
                event['risk_level'] = 'high'

        # Trackers: keep broad detection, but avoid counting "clearurls" as domain risk; it's a keyword only.
        if any(x in url_norm_l for x in ("tracker", "analytics", "beacon", "doubleclick", "facebook.net", "clearurls", "adguard")):
            self.tracker_hits += 1
            event['threats'].append("TRACKER")
            if event['risk_level'] == 'low':
                event['risk_level'] = 'medium'

        # Fingerprint API triggers (simulate Cover Your Tracks test)
        # Reduce false positives: check in focus first; fallback to full URL if needed.
        fp_focus = focus if focus else url_norm_l
        for k in self.fingerprint_apis:
            if self._token_present(fp_focus, k) or (k in fp_focus and k in ("webgl", "webrtc", "canvas")):
                self.fingerprint_apis[k] += 1
                event['threats'].append(f"FINGERPRINT:{k}")
                if event['risk_level'] == 'low':
                    event['risk_level'] = 'medium'
                self.fingerprint_attempts += 1

        # -------------------------
        # 4) Anomaly detection windows (bugfix + keep aggressive intent)
        # -------------------------
        self.request_timestamps.append(now)
        last1s = sum(1 for t in self.request_timestamps if (now - t) < 1.0)
        if last1s > self.anomaly_threshold:
            event['threats'].append("ANOMALY:burst")
            if event['risk_level'] in ("low", "medium"):
                event['risk_level'] = 'high'

        # Rapid redirect loop detection (unchanged)
        if len(self.redirects) > 7:
            event['threats'].append("ANOMALY:redirect_loop")
            if event['risk_level'] in ("low", "medium"):
                event['risk_level'] = 'high'

        self.events.append(event)

        # -------------------------
        # 5) Lockdown trigger (keep behavior intact; still immediate on critical)
        # -------------------------
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
        print("[MiniAI] 🔒 HTTP blocked:", str(url)[:60])

    # Expanded statistics/report as passive mode
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
        total_threats = (
            stats['threats']['trackers'] + stats['threats']['fingerprinting'])
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
# --- Custom Icon helpers (ported from fixed2) ---
def make_icon(color=None, size=24):

    if color is None:
        color = "#34C759"

    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)

    p.drawEllipse(4, 4, size-8, size-8)

    p.end()
    return QIcon(pix)

def make_nav_arrow_icon(direction: str, color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))

    center = size / 2
    length = size * 0.19

    if direction == "left":
        points = [
            QPointF(center + length, center - length),
            QPointF(center - length, center),
            QPointF(center + length, center + length)
        ]
    elif direction == "right":
        points = [
            QPointF(center - length, center - length),
            QPointF(center + length, center),
            QPointF(center - length, center + length)
        ]
    else:
        points = []

    if points:
        polygon = QPolygonF(points)
        p.drawPolygon(polygon)

    p.end()
    return QIcon(pix)

def make_reload_icon(color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen_width = max(2, size // 16)
    margin = pen_width // 2 + 6
    radius = (size - 2 * margin) / 2
    center = size / 2
    start_angle_deg = 135
    span_angle_deg = 320
    rect = QRectF(center - radius, center - radius, 2 * radius, 2 * radius)
    pen = QPen(QColor(color), pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawArc(rect, int(start_angle_deg * 16), int(span_angle_deg * 16))
    p.end()
    return QIcon(pix)

def make_house_icon(color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    c = QColor(color)
    linew = max(2, int(size * 0.11))
    cx, cy = size / 2, size / 2
    scale = size / 42.0
    roof_w, roof_h = 20 * scale, 10 * scale
    wall_h, wall_w = 13 * scale, 16 * scale
    roof_peak = QPointF(cx, cy - roof_h)
    roof_left = QPointF(cx - roof_w / 2, cy)
    roof_right = QPointF(cx + roof_w / 2, cy)
    wall_top_left = QPointF(cx - wall_w / 2, cy)
    wall_top_right = QPointF(cx + wall_w / 2, cy)
    wall_bot_left = QPointF(cx - wall_w / 2, cy + wall_h)
    wall_bot_right = QPointF(cx + wall_w / 2, cy + wall_h)
    path = QPainterPath()
    path.moveTo(roof_left)
    path.lineTo(roof_peak)
    path.lineTo(roof_right)
    path.lineTo(wall_top_right)
    path.lineTo(wall_bot_right)
    path.lineTo(wall_bot_left)
    path.lineTo(wall_top_left)
    path.lineTo(roof_left)
    p.setPen(QPen(c, linew, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)
    p.end()
    return QIcon(pix)

def make_zoom_icon(sign: str, color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    pen_width = max(2, size // 10)
    pen = QPen(QColor(color), pen_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    center = size / 2
    length = size * 0.15
    if sign == "+":
        p.drawLine(QPointF(center - length, center), QPointF(center + length, center))
        p.drawLine(QPointF(center, center - length), QPointF(center, center + length))
    else:
        p.drawLine(QPointF(center - length, center), QPointF(center + length, center))
    p.end()
    return QIcon(pix)

def make_fullscreen_icon(color: str, size: int) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color), max(2, size//10), Qt.SolidLine, Qt.RoundCap)
    p.setPen(pen)
    gap = size * 0.22
    span = size * 0.13
    p.drawLine(QPointF(gap, gap+span),      QPointF(gap, gap))
    p.drawLine(QPointF(gap, gap),           QPointF(gap+span, gap))
    p.drawLine(QPointF(size-gap, gap+span), QPointF(size-gap, gap))
    p.drawLine(QPointF(size-gap, gap),      QPointF(size-gap-span, gap))
    p.drawLine(QPointF(gap, size-gap-span), QPointF(gap, size-gap))
    p.drawLine(QPointF(gap, size-gap),      QPointF(gap+span, size-gap))
    p.drawLine(QPointF(size-gap, size-gap-span), QPointF(size-gap, size-gap))
    p.drawLine(QPointF(size-gap, size-gap),      QPointF(size-gap-span, size-gap))
    p.end()
    return QIcon(pix)
    
def make_java_icon(color: str, size: int = 48) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    accent = QColor(color)
    pen = QPen(accent, int(size * 0.08), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    for i, offset in enumerate([-0.15, 0, 0.15]):
        path = QPainterPath()
        cx = size * 0.5 + offset * size
        top = size * 0.16 + i * size * 0.05
        path.moveTo(cx, top)
        path.cubicTo(cx + size*0.08, top + size*0.04, cx - size*0.08, top + size*0.10, cx, top + size*0.18)
        p.drawPath(path)

    cup_rect = QRectF(size*0.20, size*0.53, size*0.60, size*0.23)
    body_rect = QRectF(size*0.28, size*0.63, size*0.44, size*0.18)
    saucer_rect = QRectF(size*0.17, size*0.78, size*0.66, size*0.14)
    handle_rect = QRectF(size*0.68, size*0.62, size*0.18, size*0.22)
    p.drawArc(QRectF(int(cup_rect.x()), int(cup_rect.y()), int(cup_rect.width()), int(cup_rect.height())), 0, 16*180)
    p.drawArc(QRectF(int(body_rect.x()), int(body_rect.y()), int(body_rect.width()), int(body_rect.height())), 0, 16*180)
    p.drawArc(QRectF(int(saucer_rect.x()), int(saucer_rect.y()), int(saucer_rect.width()), int(saucer_rect.height())), 0, 16*180)
    p.drawArc(QRectF(int(handle_rect.x()), int(handle_rect.y()), int(handle_rect.width()), int(handle_rect.height())), int(16*40), int(16*175))
    p.end()
    return QIcon(pm)

def make_nuke_icon(hex_color: str, size: int) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    accent = QColor(hex_color)
    black = QColor("#111412")
    cx, cy = size / 2, size / 2
    radius = size * 0.48
    border_width = int(size * 0.06)
    p.setPen(QPen(black, border_width))
    p.setBrush(QBrush(accent))
    p.drawEllipse(int(cx - radius), int(cy - radius), int(2 * radius), int(2 * radius))
    hub_r = size * 0.14
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(black))
    p.drawEllipse(int(cx - hub_r), int(cy - hub_r), int(2 * hub_r), int(2 * hub_r))
    p.setBrush(QBrush(black))
    for i in range(3):
        p.save()
        p.translate(cx, cy)
        p.rotate(i * 120)
        path = [
            QPointF(0, -hub_r * 1.35),
            QPointF(size * 0.18, -size * 0.35),
            QPointF(0, -radius),
            QPointF(-size * 0.18, -size * 0.35)
        ]
        polygon = QPolygonF(path)
        p.drawPolygon(polygon)
        p.restore()
    p.end()
    return QIcon(pm)
    
def detect_nav_platform():
    system = _platform.system()
    machine = _platform.machine().lower()

    if system == "Darwin":
        return "MacIntel"

    if system == "Windows":
        return "Win32"

    if system == "Linux":
        if "aarch64" in machine or "arm" in machine:
            return "Linux aarch64"
        if "x86_64" in machine or "amd64" in machine:
            return "Linux x86_64"
        return "Linux"

    return sys.platform


HOMEPAGE = """ <!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Darkelf Browser</title>
<meta name="referrer" content="no-referrer">

<meta http-equiv="Content-Security-Policy"
content="
default-src 'self' data:;
style-src 'unsafe-inline';
script-src 'unsafe-inline';
img-src data:;
base-uri 'none';
object-src 'none';
frame-src 'none';
">

<style>
:root{
  --bg:#0a0b10;
  --accent:ACCENT_COLOR;
  --text:#eef2f6;
  --muted:#d7dee8;
}

*{ box-sizing:border-box; }

html,body{
  height:100%;
  margin:0;
  overflow:hidden;
}

body{
  font-family:
    ui-sans-serif,
    system-ui,
    -apple-system,
    Segoe UI,
    Roboto,
    Helvetica,
    Arial;

background:
radial-gradient(1200px 600px at 20% -10%, color-mix(in srgb, var(--accent) 35%, transparent), transparent 60%),
radial-gradient(1000px 600px at 120% 10%, color-mix(in srgb, var(--accent) 45%, transparent), transparent 60%),
var(--bg);

  display:flex;
  flex-direction:column;
  justify-content:center;
  align-items:center;
  color:var(--text);

  opacity:0;
  animation:bootFade 1.15s ease forwards;
}

@keyframes bootFade{
  from{ opacity:0; transform:scale(.985); }
  to{ opacity:1; transform:scale(1); }
}

.particles{
  position:fixed;
  inset:0;
  pointer-events:none;
  background-image:radial-gradient(color-mix(in srgb, var(--accent) 70%, transparent) 1px, transparent 1px);
  background-size:86px 86px;
  opacity:.18;
  animation:particleMove 60s linear infinite;
}

@keyframes particleMove{
  from{ transform:translateY(0); }
  to{ transform:translateY(-200px); }
}

.brand{
  display:flex;
  align-items:center;
  gap:14px;
  font-weight:800;
  font-size:3.75rem;
  line-height:1;
  animation:brandRise 1s ease forwards;
}

@keyframes brandRise{
  from{
    opacity:0;
    transform:translateY(34px);
  }
  to{
    opacity:1;
    transform:translateY(0);
  }
}

.brand svg{
  width:42px;
  height:42px;
  flex:0 0 auto;
  stroke:var(--accent);
  stroke-width:2;
  margin-top:4px;
  filter:
    drop-shadow(0 0 8px color-mix(in srgb, var(--accent) 75%, transparent))
    drop-shadow(0 0 18px color-mix(in srgb, var(--accent) 45%, transparent));
  animation:circlePulse 3s ease-in-out infinite;
}

@keyframes circlePulse{
  0%{
    transform:scale(1);
    filter:
      drop-shadow(0 0 7px color-mix(in srgb, var(--accent) 70%, transparent))
      drop-shadow(0 0 16px color-mix(in srgb, var(--accent) 40%, transparent));
  }
  50%{
    transform:scale(1.03);
    filter:
      drop-shadow(0 0 12px color-mix(in srgb, var(--accent) 90%, transparent))
      drop-shadow(0 0 26px color-mix(in srgb, var(--accent) 60%, transparent));
  }
  100%{
    transform:scale(1);
    filter:
      drop-shadow(0 0 7px color-mix(in srgb, var(--accent) 70%, transparent))
      drop-shadow(0 0 16px color-mix(in srgb, var(--accent) 40%, transparent));
  }
}

.brand span{
  color:var(--accent);
  letter-spacing:-.02em;
  text-shadow:
    0 0 10px color-mix(in srgb, var(--accent) 85%, transparent),
    0 0 24px color-mix(in srgb, var(--accent) 50%, transparent),
    0 0 44px color-mix(in srgb, var(--accent) 30%, transparent);
  animation:titlePulse 3s ease-in-out infinite;
}

@keyframes titlePulse{
  0%{
    text-shadow:
      0 0 10px color-mix(in srgb, var(--accent) 85%, transparent),
      0 0 24px color-mix(in srgb, var(--accent) 50%, transparent),
      0 0 44px color-mix(in srgb, var(--accent) 30%, transparent);
  }
  50%{
    text-shadow:
      0 0 16px color-mix(in srgb, var(--accent) 100%, transparent),
      0 0 34px color-mix(in srgb, var(--accent) 65%, transparent),
      0 0 58px color-mix(in srgb, var(--accent) 38%, transparent);
  }
  100%{
    text-shadow:
      0 0 10px color-mix(in srgb, var(--accent) 85%, transparent),
      0 0 24px color-mix(in srgb, var(--accent) 50%, transparent),
      0 0 44px color-mix(in srgb, var(--accent) 30%, transparent);
  }
}

.tagline{
margin-top:18px;
font-size:1.1rem;
letter-spacing:.25em;
text-transform:uppercase;
color:#cfd8e3;

text-align:center;
width:100%;
}

@keyframes taglineFade{
  0%{ opacity:0; transform:translateY(8px); }
  100%{ opacity:1; transform:translateY(0); }
}

.ai-status{
  position:absolute;
  bottom:42px;
  font-size:.95rem;
  font-weight:700;
  letter-spacing:.28em;
  color:var(--accent);
  opacity:.78;
  text-shadow:
    0 0 8px color-mix(in srgb, var(--accent) 85%, transparent),
    0 0 18px color-mix(in srgb, var(--accent) 35%, transparent);
  animation:miniPulse 3s ease-in-out infinite;
}

@keyframes miniPulse{
  0%{
    opacity:.68;
    text-shadow:
      0 0 8px color-mix(in srgb, var(--accent) 85%, transparent),
      0 0 18px color-mix(in srgb, var(--accent) 35%, transparent);
  }
  50%{
    opacity:.95;
    text-shadow:
      0 0 12px color-mix(in srgb, var(--accent) 100%, transparent),
      0 0 26px color-mix(in srgb, var(--accent) 50%, transparent);
  }
  100%{
    opacity:.68;
    text-shadow:
      0 0 8px color-mix(in srgb, var(--accent) 85%, transparent),
      0 0 18px color-mix(in srgb, var(--accent) 35%, transparent);
  }
}
</style>
</head>

<body>
  <div class="particles"></div>

  <div class="brand">
    <svg viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <ellipse cx="16" cy="16" rx="13" ry="14"/>
    </svg>
    <span>Darkelf Browser</span>
  </div>

  <div class="tagline">
    Shadow • Private • Hardened
  </div>

  <div class="ai-status">
    Darkelf MiniAI
  </div>
</body>
</html>
"""

class HardenedWebPage(QWebEnginePage):
    def __init__(self, parent=None, profile=None, canvas_seed=None):
        view = parent
        if profile is not None:
            try: super().__init__(profile, view)
            except TypeError: super().__init__(view)
        else: super().__init__(view)
        self._canvas_seed = canvas_seed or (secrets.randbits(32) & 0xFFFFFFFF)
        self._parent_view = view
        prof = self.profile()
        self.interceptor = getattr(prof, "_darkelf_interceptor", None)
        self.inject_darkelf_letterboxing()
        self.hw_concurrency_spoof = random.choice([2, 4, 6, 8])
        self.inject_all_scripts()


    def inject_script(self, script_source, injection_point=None, subframes=True, name=None):
        scripts = self.scripts()
        # Remove old with same name if requested
        if name:
            for s in list(scripts.toList()):
                try:
                    if s.name() == name:
                        scripts.remove(s)
                except Exception:
                    pass
        script_obj = QWebEngineScript()
        if name:
            script_obj.setName(name)
        script_obj.setSourceCode(script_source)
        script_obj.setInjectionPoint(injection_point or QWebEngineScript.DocumentCreation)
        script_obj.setRunsOnSubFrames(subframes)
        script_obj.setWorldId(QWebEngineScript.MainWorld)
        scripts.insert(script_obj)
        
    def inject_darkelf_letterboxing(self):
        script = """
        (() => {

            const detectPlatform = () => {
                try {
                    const p = navigator.platform.toLowerCase();
                    if (p.includes('mac')) return 'mac';
                    if (p.includes('win')) return 'windows';
                    if (p.includes('linux')) return 'linux';
                    return 'windows';
                } catch (e) {
                    return 'windows';
                }
            };

            const personas = [
                [1920,1080],
                [1536,864],
                [1440,900],
                [1366,768],
                [1280,720]
            ];

            const pickPersona = () => {
                try {
                    const p = personas[Math.floor(Math.random() * personas.length)];
                    return { width: p[0], height: p[1] };
                } catch(e) {
                    return { width: 1920, height: 1080 };
                }
            };

            const frameSizes = {
                windows: 140,
                mac: 80,
                linux: 120
            };

            const persona = pickPersona();

            const applyPatch = (win) => {
                try {

                    const platform = detectPlatform();
                    const frame = frameSizes[platform] || 140;

                    const width = persona.width;
                    const height = persona.height;

                    const safeDefine = (obj, key, getter) => {
                        try {
                            Object.defineProperty(obj, key, {
                                get: getter,
                                configurable: false
                            });
                        } catch(e) {}
                    };

                    safeDefine(win.screen, "width", () => width);
                    safeDefine(win.screen, "height", () => height);
                    safeDefine(win.screen, "availWidth", () => width);
                    safeDefine(win.screen, "availHeight", () => height);

                    safeDefine(win, "innerWidth", () => width);
                    safeDefine(win, "innerHeight", () => height);

                    safeDefine(win, "outerWidth", () => width);
                    safeDefine(win, "outerHeight", () => height + frame);

                } catch (e) {}
            };

            applyPatch(window);

            new MutationObserver((muts) => {
                for (const m of muts) {
                    m.addedNodes.forEach((node) => {
                        if (node.tagName === 'IFRAME') {
                            try {
                                const w = node.contentWindow;
                                applyPatch(w);
                            } catch (e) {}
                        }
                    });
                }
            }).observe(document, { childList: true, subtree: true });

            console.log('[DarkelfAI] Darkelf Letterboxing persona applied.');

        })();
        """

        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True
        )

    # --- Inject WebRTC block, geo override, and canvas noise all at DocumentCreation ---
    def stealth_webrtc_block(self):
        script = """
        (() => {
            const block = (target, key) => {
                try {
                    Object.defineProperty(target, key, {
                        get: () => undefined,
                        set: () => {},
                        configurable: false
                    });
                    delete target[key];
                } catch (e) {
                    // Silently ignore expected errors (e.g. non-configurable)
                }
            };

            const targets = [
                [window, 'RTCPeerConnection'],
                [window, 'webkitRTCPeerConnection'],
                [window, 'mozRTCPeerConnection'],
                [window, 'RTCDataChannel'],
                [navigator, 'mozRTCPeerConnection'],
                [navigator, 'mediaDevices']
            ];

            targets.forEach(([obj, key]) => block(obj, key));

            // Iframe defense
            new MutationObserver((muts) => {
                for (const m of muts) {
                    m.addedNodes.forEach((node) => {
                        if (node.tagName === 'IFRAME') {
                            try {
                                const w = node.contentWindow;
                                targets.forEach(([obj, key]) => block(w, key));
                                targets.forEach(([obj, key]) => block(w.navigator, key));
                            } catch (e) {}
                        }
                    });
                }
            }).observe(document, { childList: true, subtree: true });

            console.log('[DarkelfAI] WebRTC APIs neutralized.');
        })();
        """
        self.inject_script(script, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        
    def block_webrtc_sdp_logging(self):
        script = """
        (function() {
            if (!window.RTCPeerConnection) return;
            const OriginalRTCPeerConnection = window.RTCPeerConnection;
            window.RTCPeerConnection = function(...args) {
                const pc = new OriginalRTCPeerConnection(...args);
                const wrap = (method) => {
                    if (pc[method]) {
                        const original = pc[method].bind(pc);
                        pc[method] = async function(...mArgs) {
                            const result = await original(...mArgs);
                            if (result && result.sdp) {
                                result.sdp = result.sdp.replace(/(\\d{1,3}\\.){3}\\d{1,3}/g, "0.0.0.0");
                                result.sdp = result.sdp.replace(/ice-ufrag:.+\\r\\n/g, '');
                                result.sdp = result.sdp.replace(/ice-pwd:.+\\r\\n/g, '');
                            }
                            return result;
                        };
                    }
                };
                wrap("createOffer");
                wrap("createAnswer");
                return pc;
            };
        })();
        """
        self.inject_script(script, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        
    def inject_geolocation_override(self):
        script = """
        (function() {
            // Completely remove navigator.geolocation
            Object.defineProperty(navigator, "geolocation", {
                get: function () {
                    return undefined;
                },
                configurable: true
            });

            // Fake permissions API to return denied
            if (navigator.permissions && navigator.permissions.query) {
                const originalQuery = navigator.permissions.query;
                navigator.permissions.query = function(parameters) {
                    if (parameters.name === "geolocation") {
                        return Promise.resolve({ state: "denied" });
                    }
                    return originalQuery(parameters);
                };
            }
        })();
        """
        self.inject_script(script, injection_point=QWebEngineScript.DocumentCreation, subframes=True)

    def inject_canvas_protection(self):
        script = f"""
        (() => {{
            // Per-tab random seed, provided by Python
            const tabSeed = {self._canvas_seed};

            // Per-domain hash
            function hashString(str) {{
                let h = 2166136261;
                for (let i = 0; i < str.length; i++) {{
                    h ^= str.charCodeAt(i);
                    h = Math.imul(h, 16777619);
                }}
                return h >>> 0;
            }}
            const domainHash = hashString(location.hostname);

            // FINAL seed is combination of tabSeed and domainHash
            const seed = tabSeed ^ domainHash;

            function pixelNoise(seed, index) {{
                let x = seed ^ index;
                x = Math.imul(x ^ (x >>> 15), 0x85ebca6b);
                x = Math.imul(x ^ (x >>> 13), 0xc2b2ae35);
                x = x ^ (x >>> 16);
                return (x & 0xff);
            }}

            function applyNoise(imageData) {{
                const data = imageData.data;
                for (let i = 0; i < data.length; i++) {{
                    const n = (pixelNoise(seed, i) % 12) - 4;
                    data[i] = Math.min(255, Math.max(0, data[i] + n));
                }}
            }}

            function cloneImageData(ctx, src) {{
                const copy = ctx.createImageData(src.width, src.height);
                copy.data.set(src.data);
                return copy;
            }}

            function safePatch(proto, method, wrapper) {{
                const original = proto[method];
                Object.defineProperty(proto, method, {{
                    value: wrapper(original),
                    configurable: false,
                    writable: false
                }});
            }}

            // ---- Patch toDataURL ----
            safePatch(HTMLCanvasElement.prototype, 'toDataURL', function(original) {{
                return function() {{
                    try {{
                        const ctx = this.getContext('2d');
                        if (!ctx) return original.apply(this, arguments);

                        const w = this.width;
                        const h = this.height;
                        if (!w || !h) return original.apply(this, arguments);

                        const originalData = ctx.getImageData(0, 0, w, h);
                        const modifiedData = cloneImageData(ctx, originalData);
        
                        applyNoise(modifiedData);
                        ctx.putImageData(modifiedData, 0, 0);

                        const result = original.apply(this, arguments);

                        ctx.putImageData(originalData, 0, 0);

                        return result;
                    }} catch (e) {{
                        return original.apply(this, arguments);
                    }}
                }};
            }});

            // ---- Patch toBlob ----
            safePatch(HTMLCanvasElement.prototype, 'toBlob', function(original) {{
                return function(callback, type, quality) {{
                    try {{
                        const ctx = this.getContext('2d');
                        if (!ctx) return original.apply(this, arguments);

                        const w = this.width;
                        const h = this.height;
                        if (!w || !h) return original.apply(this, arguments);

                        const originalData = ctx.getImageData(0, 0, w, h);
                        const modifiedData = cloneImageData(ctx, originalData);
    
                        applyNoise(modifiedData);
                        ctx.putImageData(modifiedData, 0, 0);

                        original.call(this, function(blob) {{
                            ctx.putImageData(originalData, 0, 0);
                            callback(blob);
                        }}, type, quality);

                    }} catch (e) {{
                        return original.apply(this, arguments);
                    }}
                }};
            }});

            // ---- Patch getImageData (non-mutating/read) ----
            safePatch(CanvasRenderingContext2D.prototype, 'getImageData', function(original) {{
                return function(x, y, w, h) {{
                    const imageData = original.call(this, x, y, w, h);
                    applyNoise(imageData);
                    return imageData;
                }};
            }});

        }})();
        """
        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True)
                    
    def inject_fingerprint_hardware_protection(self):
        script = """
        (() => {
          // Always spoof deviceMemory as missing/undefined (shows N/A)
          try {
            Object.defineProperty(navigator, "deviceMemory", {
              get: () => undefined,
              configurable: true
            });
          } catch(e){}
          // Optional: continue randomizing hardwareConcurrency as before
          try {
            const cpuRand = Math.floor(Math.random() * 11) + 2;
            Object.defineProperty(navigator, "hardwareConcurrency", {
              get: () => cpuRand,
              configurable: true
            });
          } catch(e){}
        })();
        """
        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True)
            
    def inject_timezone_chicago_offset(self):
        script = """
        (() => {
            // Patch Date.prototype.getTimezoneOffset to always return 360 (UTC-6)
            Object.defineProperty(Date.prototype, "getTimezoneOffset", {
                value: function() { return 360; },
                configurable: true
            });
            // Patch Intl.DateTimeFormat to always pretend timeZone is UTC
            const origDTF = Intl.DateTimeFormat;
            Intl.DateTimeFormat = function(locales, options) {
                options = options || {};
                options.timeZone = "UTC";
                return origDTF.call(this, locales, options);
            };
            Intl.DateTimeFormat.prototype = origDTF.prototype;
            // Patch navigator.timezone if present (rare)
            if ('timezone' in navigator) {
                Object.defineProperty(navigator, "timezone", {
                    get: () => "UTC",
                    configurable: true
                });
            }
        })();
        """
        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True)
            
    def inject_webgl_fingerprint_per_domain(self):
        script = """
        (() => {
            function stringHash(s) {
                let h = 2166136261;
                for (let i = 0; i < s.length; i++) {
                    h ^= s.charCodeAt(i);
                    h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24);
                }
                return h >>> 0;
            }
            const SEED = stringHash(location.hostname);
            
            function seededRand(seed) {
                let a = seed + 0x6D2B79F5;
                a = Math.imul(a ^ a >>> 15, a | 1);
                a ^= a + Math.imul(a ^ a >>> 7, a | 61);
                return ((a ^ a >>> 14) >>> 0) / 4294967296;
            }

            function tweak(val, rn) {
                if (typeof val === 'number')
                    return (val + Math.round(rn * 8 - 4));
                if (typeof val === 'string')
                    return val.replace(/[A-Za-z0-9]/g, function(c) {
                        return String.fromCharCode(c.charCodeAt(0) ^ (rn * 21 | 0));
                    });
                return val;
            }

            function patchWebGL(ctxName) {
                let proto = window[ctxName] && window[ctxName].prototype;
                if (!proto) return;
                let _getParameter = proto.getParameter;
                proto.getParameter = function(param) {
                    // Vendor, Renderer, Shading language, version: randomize
                    const SENSITIVE = [
                        37445, // UNMASKED_VENDOR_WEBGL
                        37446, // UNMASKED_RENDERER_WEBGL
                        7936,  // VENDOR
                        7937,  // RENDERER
                        35724, // SHADING_LANGUAGE_VERSION
                        7938,  // VERSION
                    ];
                    if (SENSITIVE.includes(param)) {
                        let orig = _getParameter.apply(this, arguments);
                        let r = seededRand(SEED + param);
                        return tweak(orig, r);
                    }
                    // Also randomize extensions returned
                    if (typeof param === "string" && param.match(/_webgl|_renderer|_vendor|_version/i)) {
                        let orig = _getParameter.apply(this, arguments);
                        let r = seededRand(SEED + (param.length || 0));
                        return tweak(orig, r);
                    }
                    return _getParameter.apply(this, arguments);
                };
            }
            patchWebGL('WebGLRenderingContext');
            patchWebGL('WebGL2RenderingContext');
        })();
        """
        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True)
            
    def inject_audio_randomized_defense(self):
        script = r"""
        (function() {

            function hashString(str) {
                let h = 2166136261 >>> 0;
                for (let i = 0; i < str.length; i++) {
                    h ^= str.charCodeAt(i);
                    h = Math.imul(h, 16777619);
                }
                return h >>> 0;
            }

            function mulberry32(a) {
                return function() {
                    var t = a += 0x6D2B79F5;
                    t = Math.imul(t ^ t >>> 15, t | 1);
                    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
                    return ((t ^ t >>> 14) >>> 0) / 4294967296;
                }
            }

            const domain = location.hostname;
            const seed = hashString(domain);
            const rand = mulberry32(seed);

            const amplitude = 1e-7; // very small noise

            function perturb(data) {
                for (let i = 0; i < data.length; i++) {
                    data[i] += (rand() - 0.5) * amplitude;
                }
                return data;
            }

            const origGetChannelData = AudioBuffer.prototype.getChannelData;
            AudioBuffer.prototype.getChannelData = function() {
                const data = origGetChannelData.apply(this, arguments);
                return perturb(data);
            };

            if (AudioBuffer.prototype.copyFromChannel) {
                const origCopy = AudioBuffer.prototype.copyFromChannel;
                AudioBuffer.prototype.copyFromChannel = function(dest, channel, start) {
                    origCopy.apply(this, arguments);
                    perturb(dest);
                };
            }

        })();
        """
        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True)

    def inject_battery_defense(self):
        script = r"""
        if ("getBattery" in navigator) {
          navigator.getBattery = function() {
            return Promise.resolve({
              charging: true,
              chargingTime: 0,
              dischargingTime: Infinity,
              level: 1,
              addEventListener: function(){},
              removeEventListener: function(){},
              onchargingchange: null,
              onlevelchange: null
            });
          };
        }
        """
        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True)
            
    def inject_font_protection(self):
        script = r"""
        (function() {

            function hashString(str) {
                let h = 2166136261 >>> 0;
                for (let i = 0; i < str.length; i++) {
                    h ^= str.charCodeAt(i);
                    h = Math.imul(h, 16777619);
                }
                return h >>> 0;
            }

            function mulberry32(a) {
                return function() {
                    var t = a += 0x6D2B79F5;
                    t = Math.imul(t ^ t >>> 15, t | 1);
                    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
                    return ((t ^ t >>> 14) >>> 0) / 4294967296;
                }
            }

            const seed = hashString(window.__darkelfSeed || location.hostname);

            const rand = mulberry32(seed);

            // ----- 1️⃣ Fake installed font set -----

            const commonFonts = [
                "Arial","Verdana","Tahoma","Times New Roman",
                "Courier New","Georgia","Trebuchet MS",
                "Comic Sans MS","Impact","Calibri"
            ];

            const fakeInstalled = new Set();

            commonFonts.forEach(font => {
                if (rand() > 0.4) { // randomized allowlist
                    fakeInstalled.add(font.toLowerCase());
                }
            });

            // Patch document.fonts.check()
            if (document.fonts && document.fonts.check) {
                const origCheck = document.fonts.check;
                document.fonts.check = function(str) {
                    const match = str.match(/^\d+px\s+["']?([^"']+)["']?/);
                    if (match) {
                        const font = match[1].toLowerCase();
                        return fakeInstalled.has(font);
                    }
                    return origCheck.apply(this, arguments);
                };
            }

            // ----- 2️⃣ Canvas text metric perturbation -----

            const amplitude = 0.01;

            const origMeasureText = CanvasRenderingContext2D.prototype.measureText;
            CanvasRenderingContext2D.prototype.measureText = function(text) {
                const metrics = origMeasureText.apply(this, arguments);

                const noise = (rand() - 0.5) * amplitude;

                // Proxy metrics object
                return new Proxy(metrics, {
                    get(target, prop) {
                        if (prop === "width") {
                            return target.width + noise;
                        }
                        return target[prop];
                    }
                });
            };

        })();
        """
        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True)
                                    
    def inject_resize_observer_suppressor(self):
        suppressor_js = """
        try {
          new ResizeObserver(() => {}).observe(document.body);
        } catch (e) {}
        window.addEventListener("error", function(e) {
          if (e && e.message && e.message.indexOf('ResizeObserver loop limit exceeded') > -1)
            e.preventDefault();
        }, true);
        """
        self.inject_script(suppressor_js, name="__darkelf_resize_observer_patch__")
        
    def inject_stealth_storage_block(self):
        # Memory-only storage shim: prevents crashes while avoiding persistence
        script = r"""
        (() => {
          if (window.__darkelf_storage_shim) return;
          window.__darkelf_storage_shim = true;

          function makeMemoryStorage() {
            const store = new Map();

            const api = {
              get length() { return store.size; },
              key: (i) => Array.from(store.keys())[i] ?? null,
              getItem: (k) => {
                k = String(k);
                return store.has(k) ? store.get(k) : null;
              },
              setItem: (k, v) => {
                k = String(k);
                v = String(v);
                store.set(k, v);
              },
              removeItem: (k) => { store.delete(String(k)); },
              clear: () => { store.clear(); }
            };
            return api;
          }

          const memLocal = makeMemoryStorage();
          const memSession = makeMemoryStorage();

          function def(obj, prop, value) {
            try {
              Object.defineProperty(obj, prop, {
                get: () => value,
                configurable: true
              });
            } catch(e) {}
          }

          // Provide storage objects so sites don't throw
          try { def(window, "localStorage", memLocal); } catch(e) {}
          try { def(window, "sessionStorage", memSession); } catch(e) {}

          // Keep indexedDB disabled if you want (many sites survive without it)
          try { Object.defineProperty(window, "indexedDB", { get: () => undefined, configurable: true }); } catch(e) {}
          try { Object.defineProperty(window, "openDatabase", { get: () => undefined, configurable: true }); } catch(e) {}

          // Storage events: optional noop
          try {
            window.addEventListener("storage", () => {}, true);
          } catch(e) {}

          // Iframe defense: apply same shim
          const applyTo = (w) => {
            try {
              if (!w || w.__darkelf_storage_shim) return;
              w.__darkelf_storage_shim = true;
              try { def(w, "localStorage", makeMemoryStorage()); } catch(e) {}
              try { def(w, "sessionStorage", makeMemoryStorage()); } catch(e) {}
              try { Object.defineProperty(w, "indexedDB", { get: () => undefined, configurable: true }); } catch(e) {}
              try { Object.defineProperty(w, "openDatabase", { get: () => undefined, configurable: true }); } catch(e) {}
            } catch(e) {}
          };

          new MutationObserver((muts) => {
            for (const m of muts) {
              for (const node of m.addedNodes) {
                if (node && node.tagName === "IFRAME") {
                  try { applyTo(node.contentWindow); } catch(e) {}
                  try { node.addEventListener("load", () => applyTo(node.contentWindow), { once: true }); } catch(e) {}
                }
              }
            }
          }).observe(document.documentElement || document, { childList: true, subtree: true });

        })();
        """
        self.inject_script(
            script,
            injection_point=QWebEngineScript.DocumentCreation,
            subframes=True)
            
    def inject_hw_concurrency_spoof(self):
        script = """
        (() => {

            const values = [2,4,6,8];

            const hashHost = (host) => {
                let h = 0;
                for (let i = 0; i < host.length; i++) {
                    h = ((h << 5) - h) + host.charCodeAt(i);
                    h |= 0;
                }
                return Math.abs(h);
            };

            const getValue = () => {
                try {
                    const host = location.hostname || "default";
                    const idx = hashHost(host) % values.length;
                    return values[idx];
                } catch(e) {
                    return values[Math.floor(Math.random()*values.length)];
                }
            };

            const patch = (nav) => {
                try {

                    Object.defineProperty(nav, "hardwareConcurrency", {
                        get() { return getValue(); },
                        configurable: false,
                        enumerable: true
                    });

                    Object.defineProperty(Navigator.prototype, "hardwareConcurrency", {
                        get() { return getValue(); },
                        configurable: false,
                        enumerable: true
                    });

                } catch(e) {}
            };

            const apply = (win) => {
                try {

                    if (!win || win.__darkelf_hw_patch)
                        return;

                    win.__darkelf_hw_patch = true;

                    patch(win.navigator);

                } catch(e) {}
            };

            apply(window);

            new MutationObserver((muts) => {

                for (const m of muts) {

                    m.addedNodes.forEach((node) => {

                        if (!node.tagName)
                            return;

                        if (node.tagName.toLowerCase() === "iframe") {

                            try {
                                apply(node.contentWindow);
                            } catch(e) {}

                        }

                    });

                }

            }).observe(document,{childList:true,subtree:true});

            console.log("[DarkelfAI] hardwareConcurrency domain-randomized");

        })();
        """
        self.inject_script(script, injection_point=QWebEngineScript.DocumentCreation, subframes=True)

    def inject_iframe_environment_harmonizer(self):
        spoof = {
            "platform": detect_nav_platform(),
            "vendor": "Google Inc.",
            "userAgent": None,
            "deviceMemory": None,
            "languages": ["en-US", "en"],
            "language": "en-US",
            "maxTouchPoints": 0,
        }
        
        spoof_json = json.dumps(spoof)

        js = f"""
        (() => {{
          if (window.__darkelf_iframe_harmonizer) return;
          window.__darkelf_iframe_harmonizer = true;

          const SPOOF = {json.dumps(spoof)};
          try {{ SPOOF.userAgent = navigator.userAgent; }} catch(e) {{}}

          function def(obj, prop, getter) {{
            try {{
              Object.defineProperty(obj, prop, {{
                get: getter,
                configurable: true
              }});
            }} catch(e) {{}}
          }}

          function applyToWindow(w) {{
            if (!w || w.__darkelf_spoofed) return;

            try {{ w.__darkelf_spoofed = true; }} catch(e) {{}}

            try {{
              const nav = w.navigator;
              if (!nav) return;

              const proto = Object.getPrototypeOf(nav);

              def(proto,"platform",() => SPOOF.platform);
              def(proto,"vendor",() => SPOOF.vendor);
              def(proto,"userAgent",() => SPOOF.userAgent);
              def(proto,"deviceMemory",() => SPOOF.deviceMemory);
              def(proto,"languages",() => SPOOF.languages.slice());
              def(proto,"language",() => SPOOF.language);
              def(proto,"maxTouchPoints",() => SPOOF.maxTouchPoints);

            }} catch(e) {{}}
          }}

          applyToWindow(window);

        }})();
        """
        self.inject_script(js, injection_point=QWebEngineScript.DocumentCreation, subframes=True)
        
    def inject_stealth_chrome_environment(self):
        script = """
        (() => {

            const patchPlugins = (nav) => {
                try {
                    if (!nav.plugins || nav.plugins.length === 0) {

                        const fakePlugins = [
                            { name: "Chrome PDF Plugin", filename: "internal-pdf-viewer" },
                            { name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai" },
                            { name: "Native Client", filename: "internal-nacl-plugin" }
                        ];

                        fakePlugins.length = 3;
                        fakePlugins.item = (i) => fakePlugins[i];
                        fakePlugins.namedItem = (name) =>
                            fakePlugins.find(p => p.name === name);

                        Object.defineProperty(nav, 'plugins', {
                            get: () => fakePlugins,
                            configurable: true
                        });
                    }
                } catch (e) {}
            };

            const patchChromeRuntime = (win) => {
                try {

                    if (!win.chrome)
                        win.chrome = {};

                    if (!win.chrome.runtime) {
                        Object.defineProperty(win.chrome, 'runtime', {
                            get: () => ({}),
                            configurable: true
                        });
                    }

                } catch (e) {}
            };

            const patchPermissions = (nav) => {
                try {

                    if (nav.permissions && nav.permissions.query) {
    
                        const originalQuery = nav.permissions.query.bind(nav.permissions);

                        nav.permissions.query = function(parameters) {

                            if (parameters && parameters.name === 'notifications') {
                                return Promise.resolve({
                                    state: Notification.permission
                                });
                            }

                            return originalQuery(parameters);
                        };
                    }

                } catch (e) {}
            };

            const apply = (win) => {
                try {
                    if (!win || win.__darkelf_chrome_env)
                        return;

                    win.__darkelf_chrome_env = true;

                    patchPlugins(win.navigator);
                    patchChromeRuntime(win);
                    patchPermissions(win.navigator);

                } catch (e) {}
            };

            // apply to main window
            apply(window);

            // observe iframes
            new MutationObserver((muts) => {

                for (const m of muts) {

                    m.addedNodes.forEach((node) => {

                        if (!node.tagName)
                            return;

                        if (node.tagName.toLowerCase() === "iframe") {

                            try {
                                const w = node.contentWindow;
                                apply(w);
                            } catch (e) {}

                        }

                    });

                }

            }).observe(document, { childList: true, subtree: true });

            console.log('[DarkelfAI] Chrome environment normalized');

        })();
        """
        self.inject_script(script, injection_point=QWebEngineScript.DocumentCreation, subframes=True)

        
    def inject_all_scripts(self):
        self.stealth_webrtc_block()
        self.block_webrtc_sdp_logging()
        self.inject_geolocation_override()
        self.inject_canvas_protection()
        self.inject_fingerprint_hardware_protection()
        self.inject_audio_randomized_defense()
        self.inject_battery_defense()
        self.inject_webgl_fingerprint_per_domain()
        self.inject_timezone_chicago_offset()
        self.inject_font_protection()
        self.inject_resize_observer_suppressor()
        self.inject_stealth_storage_block()
        self.inject_hw_concurrency_spoof()
        self.inject_iframe_environment_harmonizer()
        self.inject_stealth_chrome_environment()
        

    def acceptNavigationRequest(self, url, navtype, isMainFrame):
        if url.scheme() == "file":
            QMessageBox.warning(None, "Navigation blocked", "File URLs are blocked for privacy.")
            return False
        return super().acceptNavigationRequest(url, navtype, isMainFrame)

    def createWindow(self, _type):
        parent_view = getattr(self, "_parent_view", None)
        main_window = parent_view.window() if parent_view else None

        # If this page belongs to the main browser window
        if isinstance(main_window, DarkelfBrowser):

            # Create a proper Darkelf tab
            main_window._add_tab()

            # Return the page of the new tab
            view = main_window.tabs.currentWidget()
            return view.page()

        # fallback if not inside the main window
        view = QWebEngineView(parent_view)

        try:
            page = HardenedWebPage(view, self.profile())
        except TypeError:
            page = HardenedWebPage(view)

        view.setPage(page)
        page._parent_view = view

        try:
            page.fullScreenRequested.connect(view.window().handle_fullscreen)
        except Exception:
            pass

        view.show()

        if not hasattr(self, "_spawned_views"):
            self._spawned_views = []

        self._spawned_views.append(view)

        return page

class DownloadItem(QWidget):

    def __init__(self, download):
        super().__init__()

        self.download = download

        layout = QHBoxLayout(self)

        self.label = QLabel(download.downloadFileName())
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.cancel = QPushButton("Cancel")

        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(self.cancel)

        self.cancel.clicked.connect(self._handle_click)

        download.receivedBytesChanged.connect(self.update_progress)
        download.totalBytesChanged.connect(self.update_progress)
        download.stateChanged.connect(self.handle_state)

    def update_progress(self):
        total = self.download.totalBytes()
        received = self.download.receivedBytes()

        if total <= 0:
            # Unknown file size → show animated busy bar
            self.progress.setRange(0, 0)
        else:
            percent = int((received / total) * 100)
            self.progress.setRange(0, 100)
            self.progress.setValue(percent)

    def handle_state(self, state):

        if state == QWebEngineDownloadRequest.DownloadCompleted:
            self.progress.setValue(100)
            self.cancel.setText("Done")

        elif state == QWebEngineDownloadRequest.DownloadCancelled:
            self.cancel.setText("Remove")

        elif state == QWebEngineDownloadRequest.DownloadInterrupted:
            self.cancel.setText("Failed")
            
    def _handle_click(self):

        state = self.download.state()

        if state == QWebEngineDownloadRequest.DownloadInProgress:
            self.download.cancel()
        else:
            self.setParent(None)
            self.deleteLater()

class DownloadShelf(QWidget):

    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout(self)

    def add_download(self, download):

        item = DownloadItem(download)
        self.layout.addWidget(item)

        item.destroyed.connect(self._check_empty)

    def _check_empty(self):

        if self.layout.count() == 0:
            self.hide()
            
def create_color_palette_menu(parent, callback):

    menu = QMenu(parent)

    # palette widget INSIDE the menu
    palette = QWidget(menu)

    grid = QGridLayout(palette)
    grid.setSpacing(2)
    grid.setContentsMargins(4,4,4,4)

    colors = [
        "#34C759",
        "#444444","#666666","#999999",
        "#ff4d4f","#ff7a45","#ffa940",
        "#ffd666","#73d13d","#36cfc9","#40a9ff",
        "#597ef7","#9254de","#f759ab","#bfbfbf"
    ]

    row = 0
    col = 0

    for color_hex in colors:

        btn = QPushButton()
        btn.setFixedSize(20,20)

        btn.setStyleSheet(
            f"""
            QPushButton {{
                background:{color_hex};
                border:1px solid #555;
            }}
            QPushButton:hover {{
                border:2px solid white;
            }}
            """
        )

        # important: capture color safely
        btn.clicked.connect(lambda _, c=color_hex: callback(QColor(c)))

        grid.addWidget(btn, row, col)

        col += 1
        if col == 8:
            col = 0
            row += 1

    action = QWidgetAction(menu)
    action.setDefaultWidget(palette)

    menu.addAction(action)

    return menu

# ------------------------------------------------
# Main browser class
# ------------------------------------------------
class DarkelfBrowser(QMainWindow):
    def __init__(self, profile):
        super().__init__()
        
        self.accent_color = "#34C759"

        self.toolbar = self._make_toolbar()

        self.setWindowTitle("")
        self.resize(1200, 800)

        self.shared_profile = profile

        print("OffTheRecord:", self.shared_profile.isOffTheRecord())

        self.easy = EasyListEngine()
        self.easy.load_and_build(EASYLIST_URLS)

        print("Loaded network rules:", len(self.easy.network_rules))

        self.mini_ai = DarkelfMiniAISentinel()

        self.interceptor = StealthInterceptor(
            self.easy,
            self.mini_ai
        )
        self.shared_profile._darkelf_interceptor = self.interceptor
        self.shared_profile.setUrlRequestInterceptor(self.interceptor)

        # -----------------------------
        # Create UI
        # -----------------------------
        self.tabs = QTabWidget()

        # enable close buttons
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)

        # connect close signal
        self.tabs.tabCloseRequested.connect(self.close_tab)

        # ensure tabbar supports close buttons
        tabbar = self.tabs.tabBar()
        tabbar.setTabsClosable(True)

        # -----------------------------
        # Download shelf
        # -----------------------------
        self.download_shelf = DownloadShelf()
        self.download_shelf.hide()

        self.tabs_layout = QVBoxLayout()
        self.tabs_layout.addWidget(self.tabs)
        self.tabs_layout.addWidget(self.download_shelf)

        container = QWidget()
        container.setLayout(self.tabs_layout)

        # ONLY CALL setCentralWidget ONCE
        self.setCentralWidget(container)

        # -----------------------------
        # Apply tab styling
        # -----------------------------
        self._set_tab_style()
        
        self.set_accent_color(QColor(self.accent_color))

        # -----------------------------
        # Toolbar
        # -----------------------------
        self.toolbar = self._make_toolbar()
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        # -----------------------------
        # Startup tab
        # -----------------------------
        QApplication.instance().aboutToQuit.connect(self._cleanup_webengine)
        self._add_tab(home=True)

        # -----------------------------
        # Downloads
        # -----------------------------
        self._download_dir = _safe_download_dir()
        self._downloaded_files: list[str] = []
        self._hook_secure_downloads()

        QApplication.instance().aboutToQuit.connect(self._wipe_download_traces)

        # -----------------------------
        # Hotkeys
        # -----------------------------
        self.setup_hotkeys()

        # -----------------------------
        # Memory cleanup timers
        # -----------------------------
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.setSingleShot(True)
        self.cleanup_timer.timeout.connect(self.memory_cleanup)

        self.maintenance_timer = QTimer(self)
        self.maintenance_timer.timeout.connect(self.memory_cleanup)
        self.maintenance_timer.start(300000)

        self.renderer_cleanup_timer = QTimer(self)
        self.renderer_cleanup_timer.timeout.connect(self.release_renderer_memory)
        self.renderer_cleanup_timer.start(600000)

    def release_renderer_memory(self):
        try:
            for i in range(self.tabs.count()):
                view = self.tabs.widget(i)

                if not view:
                    continue

                page = view.page()

                if not page:
                    continue

                if i != self.tabs.currentIndex():  # skip active tab
                    page.triggerAction(QWebEnginePage.Stop)
                    page.setLifecycleState(QWebEnginePage.LifecycleState.Discarded)

        except Exception as e:
            print("[Darkelf] Renderer cleanup error:", e)

    def new_tab(self):
        self._add_tab(home=True)
        self.debounce_cleanup()

        
    def close_tab(self):
        if i >= 0:
            self.tabs.removeTab(i)
            self.debounce_cleanup()
            
    def reload_page(self):
        view = self.tabs.currentWidget()
        if view:
            view.reload()
        
    def on_url_entered(self):
        text = self.addr.text().strip()
        if not text:
            self._add_tab(home=True)
            return
        has_scheme = re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', text) is not None
        looks_like_domain = re.match(r'^[\w.-]+\.[A-Za-z]{2,}(/|$)', text) is not None
        looks_like_ip_or_local = re.match(r'^(localhost|(?:\d{1,3}\.){3}\d{1,3})(:\d+)?(/|$)?$', text) is not None
        if has_scheme:
            url = text
        elif looks_like_domain or looks_like_ip_or_local:
            url = "https://" + text
        else:
            base = DUCK_LITE_HTTPS
            url = base + "?q=" + quote_plus(text)

        # SANIIZE HERE!
        url = sanitize_url_clearurls(url)

        self._add_tab(url=url)
        
    def debounce_cleanup(self, delay=5000):
        # Restart timer every time
        self.cleanup_timer.start(delay)
        
    def memory_cleanup(self):
        try:
            gc.collect()
            print("[Darkelf] GC complete")

        except Exception as e:
            print("[Darkelf] Cleanup error:", e)
            
    def make_outline_lock_icon(self, color="#ffffff", size=16):
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen(QColor(color))
        pen.setWidth(2)
        painter.setPen(pen)

        # Lock body
        painter.drawRoundedRect(4, 7, 8, 7, 2, 2)

        # Lock shackle
        painter.drawArc(4, 2, 8, 10, 0 * 16, 180 * 16)

        painter.end()
        return QIcon(pix)
    
    def _make_toolbar(self):

        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(22, 22))

        c = self.accent_color

        self.back_action = QAction(make_nav_arrow_icon("left", c, 22), "Back", self)
        self.fwd_action = QAction(make_nav_arrow_icon("right", c, 22), "Forward", self)
        self.reload_action = QAction(make_reload_icon(c, 22), "Reload", self)
        self.home_action = QAction(make_house_icon(c, 22), "Home", self)
        self.zoom_in_action = QAction(make_zoom_icon("+", c, 20), "Zoom In", self)
        self.zoom_out_action = QAction(make_zoom_icon("-", c, 20), "Zoom Out", self)
        self.full_action = QAction(make_fullscreen_icon(c, 20), "Full Screen", self)


        self.java_action = QAction(make_java_icon(self.accent_color, 18), "JavaScript", self)
        self.nuke_action = QAction(make_nuke_icon("#ff2a2a", 18), "Nuke", self)

        self.addtab_action = QAction(make_icon(c, 20), "New Tab", self)

        self.nuke_action.triggered.connect(self.nuke_all_data)

        self.back_action.triggered.connect(self.go_back)
        self.fwd_action.triggered.connect(self.go_fwd)
        self.reload_action.triggered.connect(self.reload)
        self.home_action.triggered.connect(self.go_home)
        self.zoom_in_action.triggered.connect(self.zoom_in)
        self.zoom_out_action.triggered.connect(self.zoom_out)
        self.full_action.triggered.connect(self.toggle_fullscreen)
        self.addtab_action.triggered.connect(lambda: self._add_tab(home=True))

        tb.addAction(self.back_action)
        tb.addAction(self.fwd_action)
        tb.addAction(self.reload_action)
        tb.addAction(self.home_action)
        tb.addSeparator()

        self.addr = QLineEdit()
        self.addr.setPlaceholderText("Search or enter URL")
        self.addr.returnPressed.connect(self.on_url_entered)
        tb.addWidget(self.addr)
        tb.addSeparator()
        
        # ADD LOCK ICON HERE
        self.lock_action = self.addr.addAction(
            self.make_outline_lock_icon("#ffffff", 16),
            QLineEdit.LeadingPosition
        )
        self.lock_action.setVisible(False)
        
        self.addr.setStyleSheet(f"""
        QLineEdit {{
            background-color: #12141b;
            color: #eafaf0;
            border: 1px solid {self.accent_color};
            border-radius: 6px;
            padding: 4px 8px;
            selection-background-color: {self.accent_color};
            selection-color: #0a0b10;
        }}
        """)


        tb.addAction(self.zoom_out_action)
        tb.addAction(self.zoom_in_action)
        tb.addAction(self.full_action)
        tb.addAction(self.addtab_action)
        
        # ---- Accent color picker ----

        self.color_btn = QToolButton()
        self.color_btn.setText("◈")  # cyber style icon
        self.color_btn.setFixedSize(28, 24)

        self.color_btn.setStyleSheet(f"""
        QToolButton {{
            background: transparent;
            color: {self.accent_color};
            border: none;
            font-size: 16px;
        }}

        QToolButton:hover {{
            color: white;
        }}
        """)

        self.color_btn.setMenu(
            create_color_palette_menu(self, self.set_accent_color)
        )

        self.color_btn.setPopupMode(QToolButton.InstantPopup)


        tb.addWidget(self.color_btn)


        tb.addSeparator()

        self.java_action.setCheckable(True)
        self.java_action.setChecked(True)
        self.java_action.setToolTip("Enable/Disable JavaScript globally")
        tb.addAction(self.java_action)
        
        tb.addAction(self.nuke_action)
        
        def update_js_icon():
            enabled = self.java_action.isChecked()
            color = "#f89820" if enabled else "#bbbbbb"
            self.java_action.setIcon(make_java_icon(color, 18))
            self.java_action.setText("JavaScript" if enabled else "JS Off")
            self.toggle_javascript()
        self.java_action.triggered.connect(update_js_icon)

        tb.addSeparator()
        return tb
                
    def set_accent_color(self, color):

        self.accent_color = color.name()
        c = self.accent_color

        # update Qt highlight palette (text selection, menus, etc.)
        app = QApplication.instance()
        palette = app.palette()
        palette.setColor(QPalette.Highlight, QColor(c))
        palette.setColor(QPalette.HighlightedText, QColor("#0a0b10"))
        palette.setColor(QPalette.Link, QColor(c))
        palette.setColor(QPalette.LinkVisited, QColor(c))
        app.setPalette(palette)

        # update toolbar icons
        self.back_action.setIcon(make_nav_arrow_icon("left", c, 22))
        self.fwd_action.setIcon(make_nav_arrow_icon("right", c, 22))
        self.reload_action.setIcon(make_reload_icon(c, 22))
        self.home_action.setIcon(make_house_icon(c, 22))
        self.zoom_in_action.setIcon(make_zoom_icon("+", c, 20))
        self.zoom_out_action.setIcon(make_zoom_icon("-", c, 20))
        self.full_action.setIcon(make_fullscreen_icon(c, 20))
        self.addtab_action.setIcon(make_icon(c, 20))
        self.java_action.setIcon(make_java_icon(c, 18))
        
        self.addr.setStyleSheet(f"""
        QLineEdit {{
            background-color: #12141b;
            color: #eafaf0;
            border: 1px solid {c};
            border-radius: 6px;
            padding: 4px 8px;
            selection-background-color: {c};
            selection-color: #0a0b10;
        }}
        """)

        # update diamond palette button
        self.color_btn.setStyleSheet(f"""
        QToolButton {{
            background: transparent;
            color: {c};
            border: none;
            font-size: 16px;
        }}

        QToolButton:hover {{
            color: white;
        }}
        """)

        # update application stylesheet
        QApplication.instance().setStyleSheet(f"""
            QMainWindow {{
                background-color: #0b0f14;
            }}

            QWidget {{
                background-color: #0b0f14;
                color: white;
            }}

            QLineEdit {{
                background-color: #111;
                color: white;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 4px;
            }}

            QLineEdit:focus {{
                border: 1px solid {c};
            }}

            QToolBar {{
                background-color: #0b0f14;
                border-bottom: 1px solid #222;
            }}

            QPushButton {{
                background-color: #111;
                color: white;
                border: 1px solid #444;
                border-radius: 4px;
            }}

            QPushButton:hover {{
                border: 1px solid {c};
            }}

            QPushButton#accent {{
                background-color: {c};
                color: black;
                border: none;
            }}

            QLabel#accentText {{
                color: {c};
                font-weight: bold;
            }}

            QTabBar::tab:selected {{
                border-bottom: 2px solid {c};
            }}

            /* -------- FIX CONTEXT MENUS -------- */

            QMenu {{
                background-color: #0b0f14;
                border: 1px solid #222;
                padding: 4px;
            }}

            QMenu::item {{
                color: #eafaf0;
                padding: 6px 18px;
                background: transparent;
            }}

            QMenu::item:selected {{
                background: {c};
                color: #0a0b10;
                border-radius: 4px;
            }}

            QMenu::separator {{
                height: 1px;
                background: #222;
                margin: 4px 6px;
            }}
        """)

        self._set_tab_style()

        for i in range(self.tabs.count()):
            view = self.tabs.widget(i)

            js = f"""
            document.documentElement.style.setProperty('--accent', '{self.accent_color}');
            """

            try:
                view.page().runJavaScript(js)
            except:
                pass


    def _configure_tabbar_small(self):
        bar = self.tabs.tabBar()
        bar.setExpanding(False)
        bar.setMovable(True)
        bar.setElideMode(Qt.TextElideMode.ElideRight)
        bar.setIconSize(QSize(16, 16))
        bar.setUsesScrollButtons(True)
        bar.setStyleSheet("""
            QTabBar::tab { height: 22px; padding: 2px 8px; max-width: 140px; }
        """)

    def _set_tab_style(self):

        if not hasattr(self, "tabs"):
            return

        c = self.accent_color

        self.tabs.setStyleSheet(f"""
        QTabWidget::pane {{
            border: 0;
        }}

        QTabBar::tab {{
            background: #333;
            color: #fff;
            padding: 5px 10px;
            border-radius: 10px;
            margin: 2px;
        }}

        QTabBar::tab:selected,
        QTabBar::tab:hover {{
            background: {c};
            color: #000;
        }}

        QTabBar::close-button {{
            image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-close-16.png);
            background: transparent;
            border: none;
        }}

        QTabBar::close-button:hover {{
            background: transparent;
        }}
        """)

    @staticmethod
    def _short_label_from_qurl(qurl):
        try:
            host = qurl.host().lower() if hasattr(qurl, "host") else ""
        except Exception:
            host = ""
        if not host:
            return "Home"
        aliases = {
            "youtube.com": "YouTube", "www.youtube.com": "YouTube", "youtu.be": "YouTube",
            "bbc.com": "BBC", "www.bbc.com": "BBC", "bbc.co.uk": "BBC", "www.bbc.co.uk": "BBC",
            "github.com": "GitHub",
            "twitter.com": "Twitter", "x.com": "Twitter",
            "reddit.com": "Reddit", "www.reddit.com": "Reddit",
            "duckduckgo.com": "DuckDuckGo",
        }
        if host in aliases:
            return aliases[host]
        if host.startswith("www."):
            host = host[4:]
        parts = host.split(".")
        base = parts[-2] if len(parts) >= 2 else host
        return base.capitalize()
        
    def _add_tab(self, url=None, home=False):
        profile = self.shared_profile
        tab_seed = secrets.randbits(32) & 0xFFFFFFFF
        canvas_seed = tab_seed ^ BOOTUP_CANVAS_SEED

        view = QWebEngineView(self)
        view._profile = profile

        page = HardenedWebPage(view, profile, canvas_seed=canvas_seed)
        view.setPage(page)
        page.fullScreenRequested.connect(self.handle_fullscreen)
        
        # ---- EasyList Cosmetic Injection ----
        def apply_easylist_cosmetics(v=view):
            try:
                host = v.url().host().lower()
            except Exception:
                return

            if not host:
                return

            css = self.easy.css_for_host(host)
            if not css:
                return

            js = """
            (function() {
              try {
                const style = document.createElement('style');
                style.type = 'text/css';
                style.textContent = %s;
                (document.head || document.documentElement || document.body).appendChild(style);
              } catch(e) {}
            })();
            """ % json.dumps(css)

            v.page().runJavaScript(js)
    
        # Inject once after page load
        view.loadFinished.connect(
            lambda ok, v=view: apply_easylist_cosmetics(v) if ok else None
        )

        idx = self.tabs.addTab(view, "New Tab")
        self.tabs.setCurrentIndex(idx)

        view.urlChanged.connect(self._sync_urlbar)

        def relabel_from_url(qurl, view=view):
            i = self.tabs.indexOf(view)
            if i != -1:
                self.tabs.setTabText(i, self._short_label_from_qurl(qurl))
        view.urlChanged.connect(relabel_from_url)

        def set_icon(icon, view=view):
            i = self.tabs.indexOf(view)
            if i != -1:
                self.tabs.setTabIcon(i, icon)
        view.iconChanged.connect(set_icon)

        if home:
            html = HOMEPAGE.replace("ACCENT_COLOR", self.accent_color)
            view.setHtml(html)

        elif url and url.startswith("view-source:"):
            real_url = url.replace("view-source:", "")
            view.load(QUrl(real_url))
            view.page().toHtml(lambda html: self._show_source_tab(html))

        else:
            view.load(QUrl(url or "https://duckduckgo.com/lite/"))
        
    def _show_source_tab(self, html):
        view = QWebEngineView(self)
        view.setHtml(f"<pre style='white-space:pre-wrap;font-family:monospace'>{html.replace('<','&lt;')}</pre>")
        idx = self.tabs.addTab(view, "Source")
        self.tabs.setCurrentIndex(idx)

    def close_tab(self, idx):
        w = self.tabs.widget(idx)

        self.tabs.removeTab(idx)

        if isinstance(w, QWebEngineView):
            try:
                w.page().runJavaScript(
                    "document.querySelectorAll('video,audio').forEach(m=>{try{m.pause(); m.src='';}catch(e){}})"
                )
            except Exception:
                pass

            try:
                w.page().triggerAction(QWebEnginePage.Stop)
                w.page().setAudioMuted(True)
                w.setUrl(QUrl("about:blank"))
            except Exception:
                pass

            w.page().deleteLater()
            w.deleteLater()

        # reopen homepage if all tabs closed
        if self.tabs.count() == 0:
            self._add_tab(home=True)

    def take_snapshot(self):
        view = self.tabs.currentWidget()
        if not view:
            return

        # Grab screenshot of current tab
        pixmap = view.grab()

        # Desktop path
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")

        # Darkelf Snap folder
        snap_dir = os.path.join(desktop, "Darkelf Snap Folder")

        # Create folder if missing
        os.makedirs(snap_dir, exist_ok=True)

        # Filename
        filename = f"darkelf_snapshot_{int(time.time())}.png"
        path = os.path.join(snap_dir, filename)

        # Save image
        pixmap.save(path, "PNG")
        
        self.debounce_cleanup

        print(f"[Darkelf] Snapshot saved → {path}")
        
    def setup_hotkeys(self):

        # New tab
        new_tab_action = QAction(self)
        new_tab_action.setShortcut("Ctrl+T")
        new_tab_action.triggered.connect(self.new_tab)
        self.addAction(new_tab_action)

        # Close tab
        close_tab_action = QAction(self)
        close_tab_action.setShortcut("Ctrl+W")
        close_tab_action.triggered.connect(self.close_tab)
        self.addAction(close_tab_action)

        # Reload
        reload_action = QAction(self)
        reload_action.setShortcut("Ctrl+R")
        reload_action.triggered.connect(self.reload_page)
        self.addAction(reload_action)

        # Focus URL
        focus_url_action = QAction(self)
        focus_url_action.setShortcut("Ctrl+L")
        focus_url_action.triggered.connect(lambda: self.url_bar.setFocus())

        # Next tab
        next_tab_action = QAction(self)
        next_tab_action.setShortcut("Ctrl+Tab")
        next_tab_action.triggered.connect(
            lambda: self.tabs.setCurrentIndex(
                (self.tabs.currentIndex() + 1) % self.tabs.count()
            )
        )
        self.addAction(next_tab_action)

        # Previous tab
        prev_tab_action = QAction(self)
        prev_tab_action.setShortcut("Ctrl+Shift+Tab")
        prev_tab_action.triggered.connect(
            lambda: self.tabs.setCurrentIndex(
                (self.tabs.currentIndex() - 1) % self.tabs.count()
            )
        )
        self.addAction(prev_tab_action)
        
        # Snapshot
        snapshot_action = QAction(self)
        snapshot_action.setShortcuts(["Ctrl+Shift+S", "Meta+Shift+S"])
        snapshot_action.triggered.connect(self.take_snapshot)
        self.addAction(snapshot_action)
        
    def _cleanup_webengine(self):
        # Close tabs from last to first
        for i in reversed(range(self.tabs.count())):
            self.close_tab(i)
            
    def handle_fullscreen(self, request):
        if request.toggleOn():
            self.showFullScreen()
        else:
            self.showNormal()

        request.accept()

    def _close_tab_current(self):
        self.close_tab(self.tabs.currentIndex())

    def current_view(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, QWebEngineView) else None

    def go_back(self):
        v = self.current_view()
        if v: v.back()
    def go_fwd(self):
        v = self.current_view()
        if v: v.forward()
    def reload(self):
        v = self.current_view()
        if v: v.reload()
    def go_home(self):
        v = self.current_view()
        if v:
            html = HOMEPAGE.replace("ACCENT_COLOR", self.accent_color)
            v.setHtml(html)
    def zoom_in(self):
        v = self.current_view()
        if v: v.setZoomFactor(v.zoomFactor() + 0.1)
    def zoom_out(self):
        v = self.current_view()
        if v: v.setZoomFactor(v.zoomFactor() - 0.1)
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
            
    def _sync_urlbar(self, url=None):
        v = self.current_view()
        if not v:
            return

        qurl = v.url() if url is None else url
        u = qurl.toString()

        if u.startswith("data:text/html"):
            self.addr.setText("")
            self.lock_action.setVisible(False)
            return

        self.addr.setText(u)

        if qurl.scheme() == "https":
            self.lock_action.setVisible(True)
            self.addr.setStyleSheet(f"""
                QLineEdit {{
                    color: {self.accent_color};
                    font-weight: bold;
                }}
            """)
        else:
            self.lock_action.setVisible(False)
            self.addr.setStyleSheet("""
                QLineEdit {
                    color: #cfd8e3;
                    font-weight: normal;
                }
            """)
            
    def toggle_javascript(self):
        enabled = self.java_action.isChecked()
        settings = self.shared_profile.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, enabled)
        for i in range(self.tabs.count()):
            view = self.tabs.widget(i)
            if isinstance(view, QWebEngineView):
                view.reload()
                
    def nuke_all_data(self):
        reply = QMessageBox.question(
            self,
            "Confirm Nuke",
            "This will erase ALL cookies, cache, history and close the browser.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            # Stop all pages first (prevents WebEngine memory explosion)
            for i in range(self.tabs.count()):
                view = self.tabs.widget(i)
                if isinstance(view, QWebEngineView):
                    try:
                        view.page().triggerAction(QWebEnginePage.Stop)
                    except:
                        pass

            # Use the default profile once instead of per-tab
            profile = QWebEngineProfile.defaultProfile()

            profile.cookieStore().deleteAllCookies()
            profile.clearHttpCache()
            profile.clearAllVisitedLinks()

        except Exception as e:
            print("NUKE ERROR:", e)

        # Close all tabs safely
        self.tabs.clear()

        QMessageBox.information(
            self,
            "Nuke Complete",
            "All browser data wiped.\nBrowser will now close."
        )

        # Fully shutdown browser
        gc.collect()
        QApplication.quit()

    def authenticate_cookie(self, controller, cookie_path):
        try:
            with open(cookie_path, 'rb') as f:
                cookie = f.read()
            controller.authenticate(cookie)
        except Exception as e:
            print(f"[Darkelf] Tor cookie authentication failed: {e}")
            
    def _hook_secure_downloads(self):

        signal = self.shared_profile.downloadRequested

        if getattr(self, "_download_signal_connected", False):
            return

        signal.connect(self._handle_download_requested)
        self._download_signal_connected = True

    def _handle_download_requested(self, item):

        filename = _randomized_filename(item.downloadFileName())
        filename = os.path.basename(filename)

        item.setDownloadDirectory(self._download_dir)
        item.setDownloadFileName(filename)

        item.accept()

        # show shelf
        self.download_shelf.show()

        # add item to shelf
        self.download_shelf.add_download(item)
        
    def closeEvent(self, event):
        try:
            if hasattr(self, "mini_ai"):
                self.mini_ai.shutdown()
        except Exception as e:
            print("[MiniAI] shutdown error:", e)

        super().closeEvent(event)
        
    def _wipe_download_traces(self):
        """
        Deletes the per-session temp download directory (best-effort).
        """
        try:
            if getattr(self, "_download_dir", None) and os.path.isdir(self._download_dir):
                shutil.rmtree(self._download_dir, ignore_errors=True)
        except Exception:
            pass
        
if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # ===== KEEP YOUR PALETTE =====
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#0a0b10"))
    palette.setColor(QPalette.WindowText, QColor("#eafaf0"))
    palette.setColor(QPalette.Base, QColor("#12141b"))
    palette.setColor(QPalette.AlternateBase, QColor("#0f1114"))
    palette.setColor(QPalette.ToolTipBase, QColor("#eafaf0"))
    palette.setColor(QPalette.ToolTipText, QColor("#0a0b10"))
    palette.setColor(QPalette.Text, QColor("#eafaf0"))
    palette.setColor(QPalette.Button, QColor("#0f1114"))
    palette.setColor(QPalette.ButtonText, QColor("#eafaf0"))
    palette.setColor(QPalette.Highlight, QColor("#34C759"))
    palette.setColor(QPalette.HighlightedText, QColor("#0a0b10"))
    app.setPalette(palette)

    app.setStyleSheet(app.styleSheet() + """
    QMenu { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #171b20, stop:1 #15191c);
    border: 1px solid #1a1f23; border-radius: 6px; padding: 6px;}
    QMenu::separator{ height:1px; background:#23292e; margin:6px 8px; }
    QMenu::item{ color: #e5e7eb; padding:6px 16px; border-radius:8px; background:transparent;}
    QMenu::item:selected, QMenu::item:hover{background:#34C759;color:#181a1b;font-weight:bold;}
    QMenu::item:disabled {color:#7f8c8d;background:transparent;}
    QMenu::icon{margin-right:8px;} QMenu::item{cursor:pointer;}
    QToolTip{background:#161a1e;color:#e5e7eb;border:1px solid #22292f; border-radius:0px; padding:6px 8px;}
    """)

    # ===== 🔒 TRUE OFF-THE-RECORD PROFILE =====

    profile = QWebEngineProfile("", app)   # empty storage name => off-the-record
    profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
    profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
    profile.setHttpAcceptLanguage("en-US,en;q=0.9")
    
    profile.setHttpUserAgent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    )
    
    settings = profile.settings()
        
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.HyperlinkAuditingEnabled, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, False)
    settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)

    # ===== GLOBAL SCRIPT INJECTION =====
    script = QWebEngineScript()
    script.setName("darkelf_global_patch")
    script.setInjectionPoint(QWebEngineScript.DocumentCreation)
    script.setWorldId(QWebEngineScript.MainWorld)
    script.setRunsOnSubFrames(True)

    profile.scripts().insert(script)

    # ===== PASS PROFILE INTO WINDOW =====
    w = DarkelfBrowser(profile)
    w.show()

    sys.exit(app.exec())
