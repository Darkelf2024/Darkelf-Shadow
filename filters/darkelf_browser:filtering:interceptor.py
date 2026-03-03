from PySide6.QtWebEngineCore import QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo
from PySide6.QtCore import QUrl
from ..utils.url_sanitize import sanitize_url_clearurls

class StealthInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    def interceptRequest(self, info):
        qurl = info.requestUrl()
        scheme = (qurl.scheme() or "").lower()
        if "browserleaks.com" in qurl.host():
            return
        if scheme in ("data", "about", "chrome", "qrc", "blob", "view-source"):
            return
        if scheme == "file":
            info.block(True)
            return
        req_url = qurl.toString()
        fp_url = info.firstPartyUrl().toString()
        # Do NOT rewrite Amazon or WAF URLs
        if "amazon." not in req_url and "awswaf.com" not in req_url:
            cleaned = sanitize_url_clearurls(req_url)
            if cleaned != req_url:
                return
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
        if req_type and req_type not in ("document", "subdocument"):
            if "amazon." not in req_url and "awswaf.com" not in req_url:
                cleaned = sanitize_url_clearurls(req_url)
                if cleaned != req_url:
                    info.redirect(QUrl(cleaned))
                    return
        try:
            if self.engine.should_block(req_url, fp_url, req_type):
                print("BLOCKED:", req_type, fp_url, "->", req_url)
                info.block(True)
                return
        except Exception as e:
            print("Interceptor error:", e)
            return
