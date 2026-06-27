# shadow/interceptor.py

import json

from PySide6.QtWebEngineCore import QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo
from PySide6.QtCore import QUrl

from shadow.filters import EasyListEngine
from shadow.utils import is_domain
from shadow.constants import CHROME_UA, WEBKIT_UA
    
class StealthInterceptor(QWebEngineUrlRequestInterceptor):

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
        # --------------------------------------------------
        # MiniAI Panic Mode
        # --------------------------------------------------
        if self.mini_ai and getattr(self.mini_ai, "panic_mode_active", False):
            print("🚨 PANIC MODE: Blocking request:", req_url[:120])
            info.block(True)
            return

        # --------------------------------------------------
        # MiniAI Lockdown Mode
        # --------------------------------------------------
        if self.mini_ai and getattr(self.mini_ai, "lockdown_active", False):
            print("🔴 LOCKDOWN MODE: Request blocked:", req_url[:120])
            info.block(True)
            return

        # --------------------------------------------------
        # Send to MiniAI
        # --------------------------------------------------
        if self.mini_ai:
            try:
                self.mini_ai.monitor_network(req_url)
            except Exception as e:
                print("MiniAI error:", e)

        # --------------------------------------------------
        # Skip safe/internal schemes
        # --------------------------------------------------
        if scheme in ("data", "about", "chrome", "qrc", "blob", "view-source"):
            return

        if scheme == "file":
            info.block(True)
            return

        # --------------------------------------------------
        # Skip localhost / private IP ranges
        # --------------------------------------------------
        if host in ("localhost", "127.0.0.1") \
           or host.startswith("192.168.") \
           or host.startswith("10.") \
           or host.startswith(tuple(f"172.{i}." for i in range(16,32))):
            return

        # --------------------------------------------------
        # SAFE HTTPS UPGRADE (VPN + CDN compatible)
        # --------------------------------------------------

        rt = info.resourceType()

        # Domains known to break with forced HTTPS (CDNs, streaming, etc.)
        HTTPS_EXEMPT = (
            "googlevideo.com",
            "ytimg.com",
            "gstatic.com",
            "cloudfront.net",
            "akamaihd.net",
            "fbcdn.net",
        )

        # Only upgrade MAIN PAGE requests (not subresources)
        if scheme == "http" and rt == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame:

            # Skip problematic domains
            if any(host.endswith(d) for d in HTTPS_EXEMPT):
                return

            try:
                https_url = QUrl(qurl)
                https_url.setScheme("https")

                # Track HSTS-like behavior
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


        # Prevent downgrade ONLY if we already upgraded before
        if scheme == "http" and host in self.hsts_hosts:
            try:
                https_url = QUrl(qurl)
                https_url.setScheme("https")
                info.redirect(https_url)
                return
            except Exception as e:
                print("HSTS redirect failed:", e)

        # --------------------------------------------------
        # Resource Type Detection
        # --------------------------------------------------
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

        # 🔥 Fast path
        if req_type in ("image", "font", "stylesheet"):
            return

        # --------------------------------------------------
        # EasyList Blocking
        # --------------------------------------------------
        try:
            fp_url = info.firstPartyUrl().toString()

            if self.engine and self.engine.should_block(req_url, fp_url, req_type):
                print("BLOCKED:", req_type, fp_url, "->", req_url)
                info.block(True)
                return
        except Exception as e:
            print("Interceptor error:", e)

    # --------------------------------------------------
    # 🔥 FIXED HEADER INJECTION
    # --------------------------------------------------
    def _apply_special_headers(self, info, host: str) -> None:
        try:
            # Normalize host
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
