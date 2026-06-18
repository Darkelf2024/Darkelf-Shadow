# backend/interceptor.py

import json

from PySide6.QtWebEngineCore import (
    QWebEngineUrlRequestInterceptor,
    QWebEngineUrlRequestInfo,
)
from PySide6.QtCore import QUrl

from .filters import EasyListEngine
from .utils import is_domain
from .constants import CHROME_UA, WEBKIT_UA


class StealthInterceptor(QWebEngineUrlRequestInterceptor):

    # Domains known to break with forced HTTPS upgrade (CDNs / streaming).
    HTTPS_EXEMPT = (
        "googlevideo.com", "ytimg.com", "gstatic.com",
        "cloudfront.net", "akamaihd.net", "fbcdn.net",
    )

    def __init__(self, engine: EasyListEngine, mini_ai):
        super().__init__()
        self.engine = engine
        self.mini_ai = mini_ai
        self.hsts_hosts = set()

    def interceptRequest(self, info):
        qurl = info.requestUrl()
        req_url = qurl.toString()
        scheme = (qurl.scheme() or "").lower()
        host = (qurl.host() or "").lower()

        self._apply_special_headers(info, host)

        # MiniAI panic / lockdown gating
        if self.mini_ai and getattr(self.mini_ai, "panic_mode_active", False):
            print("PANIC MODE: blocking request:", req_url[:120])
            info.block(True)
            return
        if self.mini_ai and getattr(self.mini_ai, "lockdown_active", False):
            print("LOCKDOWN: request blocked:", req_url[:120])
            info.block(True)
            return

        if self.mini_ai:
            try:
                self.mini_ai.monitor_network(req_url)
            except Exception as e:
                print("MiniAI error:", e)

        # Safe / internal schemes
        if scheme in ("data", "about", "chrome", "qrc", "blob", "view-source"):
            return
        if scheme == "file":
            info.block(True)
            return

        # Localhost / private ranges: leave alone
        if host in ("localhost", "127.0.0.1") \
           or host.startswith("192.168.") \
           or host.startswith("10.") \
           or host.startswith(tuple(f"172.{i}." for i in range(16, 32))):
            return

        rt = info.resourceType()

        # HTTPS upgrade for main-frame navigations
        if scheme == "http" and rt == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame:
            if any(host.endswith(d) for d in self.HTTPS_EXEMPT):
                return
            try:
                https_url = QUrl(qurl)
                https_url.setScheme("https")
                self.hsts_hosts.add(host)
                if self.mini_ai:
                    try:
                        self.mini_ai.on_http_blocked(req_url)
                    except Exception as e:
                        print("Error:", e)
                info.redirect(https_url)
                return
            except Exception as e:
                print("HTTPS upgrade failed:", e)

        # Downgrade prevention for hosts we already upgraded
        if scheme == "http" and host in self.hsts_hosts:
            try:
                https_url = QUrl(qurl)
                https_url.setScheme("https")
                info.redirect(https_url)
                return
            except Exception as e:
                print("HSTS redirect failed:", e)

        # Resource type -> ABP type name
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
                type_map[getattr(QWebEngineUrlRequestInfo.ResourceType, attr)] = name

        req_type = type_map.get(rt)
        if req_type is None and hasattr(QWebEngineUrlRequestInfo.ResourceType, "ResourceTypeMainFrame"):
            if rt == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame:
                req_type = "document"

        # Fast path: never block these
        if req_type in ("image", "font", "stylesheet"):
            return

        try:
            fp_url = info.firstPartyUrl().toString()
            if self.engine and self.engine.should_block(req_url, fp_url, req_type):
                print("BLOCKED:", req_type, fp_url, "->", req_url)
                info.block(True)
                return
        except Exception as e:
            print("Interceptor error:", e)

    def _apply_special_headers(self, info, host: str) -> None:
        try:
            host = (host or "").lower()
            if is_domain(host, "youtube.com") or is_domain(host, "youtu.be") \
               or is_domain(host, "ytimg.com") or is_domain(host, "googlevideo.com"):
                info.setHttpHeader(b"User-Agent", WEBKIT_UA)
            else:
                info.setHttpHeader(b"User-Agent", CHROME_UA)
        except Exception as e:
            print("Header error", e)


# ===================== Cosmetic injection helper =====================

def js_inject_style_tag(style_id: str, css: str) -> str:
    """Return a JS snippet that injects/updates a <style> tag with the given CSS."""
    return """
    (function(){
      try {
        var id = %s;
        var css = %s;
        var el = document.getElementById(id);
        if (!el) {
          el = document.createElement('style');
          el.id = id;
          (document.documentElement || document.head || document.body).appendChild(el);
        }
        el.textContent = css;
      } catch(e) {}
    })();
    """ % (json.dumps(style_id), json.dumps(css))
