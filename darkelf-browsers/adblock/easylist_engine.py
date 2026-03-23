import os
import re
import time
import hashlib
import urllib.request
from urllib.error import URLError, HTTPError
from PySide6.QtCore import QUrl

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
    __slots__ = ("re", "is_exception", "opts", "hint")

    def __init__(self, pattern: re.Pattern, is_exception: bool, opts: dict, hint: str | None):
        self.re = pattern
        self.is_exception = is_exception
        self.opts = opts
        self.hint = hint

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

        if not rule:
            return

        rx = _abp_rule_to_regex(rule)

        if not rx:
            return

        # Prevent pathological regex rules
        if len(rx) > 400:
            return

        try:
            cre = re.compile(rx, re.I)
        except re.error:
            return

        # Extract simple domain hint for faster matching
        hint = None
        if "||" in rule:
            try:
                hint = rule.split("||", 1)[1].split("^")[0].split("/")[0].lower()
            except Exception:
                hint = None

        self.network_rules.append(_NetRule(cre, is_exception, opts, hint))

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

        if any(x in fp_host for x in (
            "walmart.com",
            "amazon.",
            "target.com",
        )):
            return False


        if req_type is None:
            return False

        if req_type == "document":
            return False

        if req_type in ("image", "stylesheet", "font"):
            return False

        # -------------------------------------------------
        # Same-site detection
        # -------------------------------------------------
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
        # Wikimedia family
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
        # GitHub family
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


        # -------------------------------------------------
        # AWS WAF protection
        # -------------------------------------------------
        if "awswaf.com" in req_host or "token.awswaf.com" in req_host:
            return False
            
        # -------------------------------------------------
        # Amazon allowlist (prevent site breakage)
        # -------------------------------------------------
        if "amazon." in fp_host:

            AMAZON_CORE = (
                "amazon.com",
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

            if any(req_host == h or req_host.endswith("." + h) for h in AMAZON_CORE):
                return False

        # -------------------------------------------------
        # HARD TRACKER BLOCK
        # -------------------------------------------------
        HARD_TRACKERS = (
            "doubleclick.net",
            "googlesyndication.com",
            "googleadservices.com",
            "googletagmanager.com",
            "google-analytics.com",
            "connect.facebook.net",
            "facebook.net",
            "adnxs.com",
            "criteo.com",
            "taboola.com",
            "outbrain.com",
            "scorecardresearch.com",
            "quantserve.com",
        )

        if any(req_host.endswith(x) for x in HARD_TRACKERS):
            return True


        # -------------------------------------------------
        # YouTube rules (custom-only; bypass generic filters)
        # -------------------------------------------------
        if "youtube.com" in fp_host or "youtu.be" in fp_host:

            # Always allow YouTube static/media/image infrastructure
            if req_host.endswith((
                "youtube.com",
                "youtube-nocookie.com",
                "ytimg.com",
                "ggpht.com",
                "googleusercontent.com",
            )):
                # block only explicit ad endpoints on these hosts
                YT_AD_ENDPOINTS = (
                    "youtube.com/pagead/",
                    "youtube.com/pagead/l",
                    "youtube.com/api/stats/ads",
                    "youtube.com/get_midroll_info",
                    "youtube.com/youtubei/v1/player/ad",
                )

                if any(ep in u for ep in YT_AD_ENDPOINTS):
                    return True

                # allow all normal YouTube APIs/assets
                return False

            # googlevideo carries both real media and ad media
            if "googlevideo.com" in req_host:
                # ad stream hints
                if any(x in u for x in ("ctier", "oad", "adformat", "midroll")):
                    return True

                # real playback/manifests/range requests
                if any(x in u for x in ("videoplayback", "manifest", "initplayback")):
                    return False

                # safest fallback for YouTube media host
                return False

            # Let all other YouTube-related requests pass untouched
            return False

        # -------------------------------------------------
        # Third-party ad tech signals
        # -------------------------------------------------
        if req_type in ("script", "xmlhttprequest", "subdocument") and is_third_party:

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


        # -------------------------------------------------
        # Media ad blocking
        # -------------------------------------------------
        if req_type == "media" and is_third_party:

            AD_MEDIA_HOSTS = (
                "doubleclick.net",
                "googlesyndication.com",
                "googleadservices.com",
                "adnxs.com",
                "criteo.com",
                "taboola.com",
                "outbrain.com",
            )

            if any(req_host.endswith(x) for x in AD_MEDIA_HOSTS):
                return True


        # -------------------------------------------------
        # Image safety rules
        # -------------------------------------------------
        if req_type == "image":

            # allow first-party images always
            if same_site:
                return False
                
            # Allow common image CDNs
            if req_type == "image" and req_host.endswith((
                "cloudfront.net",
                "akamaized.net",
                "fastly.net",
                "imgix.net",
                "shopifycdn.com",
                "ichef.bbci.co.uk",
                "bbci.co.uk",
            )):
                return False

            # allow YouTube image infrastructure
            YT_IMAGE_HOSTS = (
                "ytimg.com",
                "ggpht.com",
                "googleusercontent.com",
            )

            if any(req_host.endswith(x) for x in YT_IMAGE_HOSTS):
                return False

            # block only obvious ad-image networks
            if is_third_party and any(k in req_host for k in (
                "doubleclick",
                "adnxs",
                "criteo",
                "taboola",
                "outbrain",
            )):
                return True

        # -------------------------------------------------
        # EasyList resource gate
        # -------------------------------------------------
        allowed_types = {
            "image",
            "media",
            "subdocument",
            "script",
            "xmlhttprequest",
        }

        if req_type not in allowed_types:
            return False
            
        #if same_site and req_type in ("stylesheet", "font"):
            #return False

        # -------------------------------------------------
        # EasyList rule evaluation
        # -------------------------------------------------
        for rule in self.network_rules:

            if rule.hint and rule.hint not in u:
                continue

            if not _domain_option_allows(fp_host, rule.opts):
                continue

            if "third-party" in rule.opts and not is_third_party:
                continue

            if "~third-party" in rule.opts and is_third_party:
                continue
    
            type_flags = {"image", "media", "subdocument", "script", "xmlhttprequest"}

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

        lines = []

        # Convert EasyList selectors to CSS
        for sel in selectors:

            # sanitize selector
            sel = sel.replace("`", "").replace("\n", "").strip()

            # skip invalid selectors
            if not sel or sel.startswith("@"):
                continue

            # skip extremely long selectors (prevents parser issues)
            if len(sel) > 500:
                continue

            lines.append(
                f"{sel} {{ display: none !important; visibility: hidden !important; }}"
            )

        # -------------------------------------------------
        # YouTube cosmetic ad blocking
        # -------------------------------------------------
        if "youtube.com" in host:
            lines += [
                ".video-ads { display:none !important; }",
                ".ytp-ad-module { display:none !important; }",
                ".ytp-ad-overlay-container { display:none !important; }",
                ".ytp-ad-player-overlay { display:none !important; }",
                ".ytp-ad-text-overlay { display:none !important; }",
                ".ytp-ad-image-overlay { display:none !important; }",
                ".ytp-ad-progress { display:none !important; }",
                ".ytp-ad-preview-container { display:none !important; }",
                ".ytp-ad-skip-button-container { display:none !important; }",
            ]

        if not lines:
            return ""

        return "\n".join(lines)
