from PySide6.QtWebEngineCore import QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo
from PySide6.QtCore import QUrl

from ..stealth.ua_spoof import (
    SPOOF_UA, SPOOF_CH_UA, SPOOF_CH_UA_MOBILE, SPOOF_CH_UA_PLATFORM,
    SPOOF_CH_UA_FULL_VERSION, SPOOF_CH_UA_FULL_VERSION_LIST,
)
from ..utils.url_sanitize import sanitize_url_clearurls

class StealthInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    def interceptRequest(self, info):
        try:
            info.setHttpHeader(b"User-Agent", SPOOF_UA.encode("utf-8"))
            info.setHttpHeader(b"Sec-CH-UA", SPOOF_CH_UA.encode("utf-8"))
            info.setHttpHeader(b"Sec-CH-UA-Mobile", SPOOF_CH_UA_MOBILE.encode("utf-8"))
            info.setHttpHeader(b"Sec-CH-UA-Platform", SPOOF_CH_UA_PLATFORM.encode("utf-8"))
            info.setHttpHeader(b"Sec-CH-UA-Full-Version", SPOOF_CH_UA_FULL_VERSION.encode("utf-8"))
            info.setHttpHeader(b"Sec-CH-UA-Full-Version-List", SPOOF_CH_UA_FULL_VERSION_LIST.encode("utf-8"))
            info.setHttpHeader(b"Sec-CH-UA-Arch", b'"x86"')
            info.setHttpHeader(b"Sec-CH-UA-Bitness", b'"64"')
            info.setHttpHeader(b"Sec-CH-UA-Model", b'""')
        except Exception:
            pass
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
