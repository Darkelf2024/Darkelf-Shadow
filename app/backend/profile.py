# backend/profile.py
#
# Hardened, off-the-record profile factory. This is the single object the
# frontend receives; it owns the web engine's privacy posture.

import secrets
import threading

from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings

from .filters import EasyListEngine, EASYLIST_URLS
from .miniai import DarkelfMiniAISentinel
from .interceptor import StealthInterceptor
from .hardening import install_hardening


class DarkelfEngine:
    """Bundle of the hardened profile and its backend services."""

    def __init__(self, parent=None, load_filters: bool = True):
        # Empty storage name => off-the-record (memory-only) in Qt6.
        self.profile = QWebEngineProfile("", parent)
        self.profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        self.profile.setHttpAcceptLanguage("en-US,en;q=0.9")

        self._apply_settings()

        # Filter engine (network + cosmetic). Built on a background thread so
        # the window opens immediately instead of waiting on ~9 filter-list
        # downloads. Until it is ready the engine has no rules (requests pass
        # through); blocking switches on the moment the lists finish loading.
        # HTTPS-upgrade and the MiniAI sentinel do not depend on these lists,
        # so they are active from the first request.
        self.engine = EasyListEngine()
        self.filters_ready = threading.Event()
        if load_filters:
            threading.Thread(
                target=self._load_filters_async,
                args=(EASYLIST_URLS,),
                name="darkelf-filter-loader",
                daemon=True,
            ).start()
        else:
            self.filters_ready.set()

        # Passive heuristic sentinel.
        self.mini_ai = DarkelfMiniAISentinel()

        # Per-request interception (block / HTTPS-upgrade).
        self.interceptor = StealthInterceptor(self.engine, self.mini_ai)
        self.profile.setUrlRequestInterceptor(self.interceptor)
        self.profile._darkelf_interceptor = self.interceptor  # keep alive

        # Profile-level fingerprint hardening (applies to every page/view).
        self.canvas_seed = secrets.randbits(32) & 0xFFFFFFFF
        install_hardening(self.profile, self.canvas_seed)

    def _load_filters_async(self, urls) -> None:
        """Build the filter rules off the UI thread, then swap them in atomically.

        load_and_build runs against a throwaway engine; only the finished rule
        sets are assigned onto the live engine. Each assignment is atomic under
        the GIL, so the interceptor never observes half-built rules.
        """
        try:
            staged = EasyListEngine()
            staged.load_and_build(urls)
            self.engine.network_rules = staged.network_rules
            self.engine.cosmetic = staged.cosmetic
            self.engine.cosmetic_exceptions = staged.cosmetic_exceptions
            print(f"[Darkelf] Filters ready: {len(staged.network_rules)} network rules")
        except Exception as e:
            print("[Darkelf] Filter load failed:", e)
        finally:
            self.filters_ready.set()

    def _apply_settings(self) -> None:
        s = self.profile.settings()
        s.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        s.setAttribute(QWebEngineSettings.PluginsEnabled, False)
        s.setAttribute(QWebEngineSettings.HyperlinkAuditingEnabled, False)
        s.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, False)
        s.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, False)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, False)
        s.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)

    # --- Privacy actions ---------------------------------------------------

    def wipe(self) -> None:
        """Erase the ACTUAL browsing profile (cookies, cache, visited links)."""
        try:
            self.profile.cookieStore().deleteAllCookies()
            self.profile.clearHttpCache()
            self.profile.clearAllVisitedLinks()
        except Exception as e:
            print("[Darkelf] wipe error:", e)

    def shutdown(self) -> None:
        try:
            self.mini_ai.shutdown()
        except Exception as e:
            print("[Darkelf] sentinel shutdown error:", e)
