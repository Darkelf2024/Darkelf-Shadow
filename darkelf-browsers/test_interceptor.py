from PySide6.QtCore import QUrl
from browser.interceptor import StealthInterceptor


class DummyInfo:
    def __init__(self, url):
        self._qurl = QUrl(url)
        self.blocked = False

    def requestUrl(self):
        return self._qurl

    def block(self, val):
        self.blocked = val

    def resourceType(self):
        return 0  # safe default

    def firstPartyUrl(self):
        return self._qurl
        
class DummyEngine:
    def should_block(self, url, first_party, req_type):
        return "ads" in url
