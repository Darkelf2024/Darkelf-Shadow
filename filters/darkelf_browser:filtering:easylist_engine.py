import os
import re
import hashlib
import urllib.request
import time
from urllib.error import URLError, HTTPError

from ..config.urls import EASYLIST_CACHE_DIR, EASYLIST_REFRESH_EVERY
from .abp_rules import (
    abp_rule_to_regex, split_rule_and_options, domain_option_allows,
)
from ..utils.domains import safe_host, base_domain, third_party_check
from ..utils.time_utils import now

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
        self.network_rules = []
        self.cosmetic = {"*": []}
        self.cosmetic_exceptions = {}

    def _cache_path_for_url(self, url: str) -> str:
        h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        return os.path.join(EASYLIST_CACHE_DIR, f"{h}.txt")

    def _should_refresh(self, path: str) -> bool:
        if not os.path.exists(path):
            return True
        age = now() - os.path.getmtime(path)
        return age > EASYLIST_REFRESH_EVERY

    def fetch_lists(self, urls: list[str]) -> list[str]:
        texts = []
        for url in urls:
            path = self._cache_path_for_url(url)
            text = ""
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
                if line.startswith("[") and line.endswith("]"):
                    continue
                if "##" in line or "#@#" in line:
                    self._parse_cosmetic(line)
                    continue
                self._parse_network(line)

    def _parse_cosmetic(self, line: str):
        is_exc = "#@#" in line
        sep = "#@#" if is_exc else "##"
        parts = line.split(sep, 1)
        if len(parts) != 2:
            return
        domain_part = parts[0].strip()
        selector = parts[1].strip()
        if not selector:
            return
        domains = [d.strip().lower() for d in domain_part.split(",") if d.strip()] if domain_part else ["*"]
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
        rule, opts = split_rule_and_options(line)
        if not rule:
            return
        rx = abp_rule_to_regex(rule)
        if not rx:
            return
        try:
            cre = re.compile(rx, re.I)
        except re.error:
            return
        self.network_rules.append(_NetRule(cre, is_exception, opts))

    def _finalize(self):
        self.network_rules.sort(key=lambda r: (not r.is_exception))
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
        fp_host = safe_host(first_party_url)
        req_host = safe_host(url)
        if not req_host:
            return False
        # Never block BrowserLeaks (testing site)
        if "browserleaks.com" in fp_host:
            print("BROWSERLEAKS ALLOW:", req_type, url)
            return False
        if req_type is None or req_type == "document":
            return False
        def site_key(host: str) -> str:
            parts = [p for p in (host or "").split(".") if p]
            if len(parts) >= 2:
                return ".".join(parts[-2:])
            return host or ""
        fp_site = site_key(fp_host)
        req_site = site_key(req_host)
        same_site = (fp_site and req_site and fp_site == req_site)
        is_third_party = (not same_site) and third_party_check(req_host, fp_host)
        # Never block critical same-site core resources
        if same_site and req_type in ("script", "xmlhttprequest", "stylesheet", "font", "media"):
            return False
        if "awswaf.com" in req_host or "token.awswaf.com" in req_host:
            return False
        # YouTube ad blocking
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
        if fp_site == "amazon.com":
            AMAZON_ESSENTIAL = (
                "media-amazon.com",
                "ssl-images-amazon.com",
                "images-amazon.com",
                "images-na.ssl-images-amazon.com",
                "m.media-amazon.com",
                "a0.awsstatic.com","a1.awsstatic.com","a2.awsstatic.com","a3.awsstatic.com",
                "a4.awsstatic.com","a5.awsstatic.com","a6.awsstatic.com","a7.awsstatic.com",
            )
            if any(req_host == h or req_host.endswith("." + h) for h in AMAZON_ESSENTIAL):
                return False
        INFRA_ALLOW = (
            "amazonaws.com",
            "cloudfront.net",
            "awswaf.com",
        )
        if any(req_host == x or req_host.endswith("." + x) for x in INFRA_ALLOW):
            return False
        HARD_TRACKERS = (
            "doubleclick.net", "googlesyndication.com", "googleadservices.com", "adservice.google.com",
            "googletagmanager.com", "google-analytics.com", "analytics.google.com",
            "connect.facebook.net", "facebook.net", "adnxs.com", "criteo.com",
            "taboola.com", "outbrain.com", "scorecardresearch.com", "quantserve.com",
        )
        if (not same_site) and any(req_host == t or req_host.endswith("." + t) for t in HARD_TRACKERS):
            return True
        if req_type in ("script", "xmlhttprequest", "subdocument") and (not same_site):
            HIGH_SIGNAL = (
                "doubleclick","googlesyndication","googleadservices","pagead","adsystem",
                "adservice","adserver","gampad","prebid","openrtb","criteo","taboola",
                "outbrain","adnxs",
            )
            if any(k in u for k in HIGH_SIGNAL):
                return True
        if req_type == "media" and (not same_site):
            AD_MEDIA_HOSTS = (
                "doubleclick.net","googlesyndication.com","googleadservices.com",
                "adnxs.com","criteo.com","taboola.com","outbrain.com",
            )
            if any(req_host == h or req_host.endswith("." + h) for h in AD_MEDIA_HOSTS):
                return True
        if req_type == "image":
            YT_IMAGE_HOSTS = (
                "ytimg.com","ggpht.com","googleusercontent.com",
            )
            if any(req_host == h or req_host.endswith("." + h) for h in YT_IMAGE_HOSTS):
                return False
        if req_type == "image" and same_site:
            return False
        IFRAME_AD_HINTS = (
            "doubleclick","googlesyndication","adservice","adnxs","taboola","outbrain",
        )
        if req_type == "subdocument" and (not same_site):
            if any(k in u for k in IFRAME_AD_HINTS):
                return True
        # EasyList network rule matching: image/media/subdoc only
        if req_type not in ("image", "media", "subdocument"):
            return False
        for rule in self.network_rules:
            if not domain_option_allows(fp_host, rule.opts):
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
        lines = [f"{sel} {{ display: none !important; visibility: hidden !important; }}" for sel in selectors if sel]
        return "\n".join(lines)
