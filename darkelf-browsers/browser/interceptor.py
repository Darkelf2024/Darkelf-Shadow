from PySide6.QtWebEngineCore import (
    QWebEngineUrlRequestInterceptor,
    QWebEngineUrlRequestInfo
)

from PySide6.QtCore import QUrl, QUrlQuery

from utils.url_utils import sanitize_url_clearurls


class StealthInterceptor(QWebEngineUrlRequestInterceptor):

    def __init__(self, engine, mini_ai=None):
        super().__init__()

        self.engine = engine
        self.mini_ai = mini_ai

        # hosts confirmed to support HTTPS
        self.hsts_hosts = set()

    # ---------------------------------------------------------
    # Main interception hook
    # ---------------------------------------------------------

    def interceptRequest(self, info):

        qurl = info.requestUrl()

        req_url = qurl.toString()

        scheme = (qurl.scheme() or "").lower()
        host = (qurl.host() or "").lower()

        # -----------------------------------------------------
        # MiniAI PANIC MODE
        # -----------------------------------------------------

        if self.mini_ai and getattr(self.mini_ai, "panic_mode_active", False):
            print("🚨 PANIC MODE BLOCK:", req_url[:120])
            info.block(True)
            return

        # -----------------------------------------------------
        # MiniAI LOCKDOWN MODE
        # -----------------------------------------------------

        if self.mini_ai and getattr(self.mini_ai, "lockdown_active", False):
            print("🔴 LOCKDOWN BLOCK:", req_url[:120])
            info.block(True)
            return

        # -----------------------------------------------------
        # Send request to MiniAI monitor
        # -----------------------------------------------------

        if self.mini_ai:
            try:
                self.mini_ai.monitor_network(req_url)
            except Exception as e:
                print("MiniAI error:", e)

        # -----------------------------------------------------
        # Skip internal schemes
        # -----------------------------------------------------

        if scheme in ("data", "about", "chrome", "qrc", "blob", "view-source"):
            return

        if scheme == "file":
            info.block(True)
            return

        # -----------------------------------------------------
        # Skip localhost and LAN addresses
        # -----------------------------------------------------

        if host in ("localhost", "127.0.0.1") \
           or host.startswith("192.168.") \
           or host.startswith("10.") \
           or host.startswith(tuple(f"172.{i}." for i in range(16,32))):
            return

        # -----------------------------------------------------
        # HTTPS upgrade
        # -----------------------------------------------------

        rt = info.resourceType()

        if scheme == "http" and rt != QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame:

            https_url = QUrl(qurl)
            https_url.setScheme("https")

            self.hsts_hosts.add(host)

            if self.mini_ai:
                self.mini_ai.on_http_blocked(req_url)

            info.redirect(https_url)
            return

        # Prevent downgrade after HTTPS known
        if scheme == "http" and host in self.hsts_hosts:

            https_url = QUrl(qurl)
            https_url.setScheme("https")

            info.redirect(https_url)
            return

        # -----------------------------------------------------
        # Strip tracking parameters
        # -----------------------------------------------------

        tracking_params = {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "fbclid",
            "gclid",
            "mc_eid"
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

        # -----------------------------------------------------
        # Detect resource type
        # -----------------------------------------------------

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

                enum_value = getattr(
                    QWebEngineUrlRequestInfo.ResourceType,
                    attr
                )

                type_map[enum_value] = name

        req_type = type_map.get(rt)

        if req_type is None:

            if hasattr(QWebEngineUrlRequestInfo.ResourceType, "ResourceTypeMainFrame"):

                if rt == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame:
                    req_type = "document"

        # -----------------------------------------------------
        # ClearURLs sanitizing
        # -----------------------------------------------------

        if req_type and req_type not in ("document", "subdocument"):

            if "amazon." not in req_url and "awswaf.com" not in req_url:

                cleaned = sanitize_url_clearurls(req_url)

                if cleaned != req_url:
                    # optional rewrite
                    # info.redirect(QUrl(cleaned))
                    return

        # -----------------------------------------------------
        # EasyList blocking
        # -----------------------------------------------------

        try:

            if self.engine and self.engine.should_block(
                req_url,
                info.firstPartyUrl().toString(),
                req_type
            ):

                print("BLOCKED:", req_type, "->", req_url)

                if self.mini_ai:
                    self.mini_ai.monitor_network(req_url)

                info.block(True)
                return

        except Exception as e:

            print("Interceptor error:", e)
