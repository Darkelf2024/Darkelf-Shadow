from PySide6.QtWebEngineCore import QWebEngineScript, QWebEnginePage
from PySide6.QtCore import QUrl
import secrets

# Stealth JS imports
from ..stealth.scripts.webrtc_block import JS as WEBRTC_BLOCK_JS
from ..stealth.scripts.webrtc_sdp_scrub import JS as WEBRTC_SDP_SCRUB_JS
from ..stealth.scripts.geolocation_block import JS as GEOLOCATION_BLOCK_JS
from ..stealth.scripts.canvas_noise import get_js as CANVAS_NOISE_JS
from ..stealth.scripts.webgl_spoof import JS as WEBGL_SPOOF_JS
from ..stealth.scripts.audio_noise import JS as AUDIO_NOISE_JS
from ..stealth.scripts.battery_spoof import JS as BATTERY_SPOOF_JS
from ..stealth.scripts.font_spoof import JS as FONT_SPOOF_JS
from ..stealth.scripts.timezone_spoof import JS as TIMEZONE_SPOOF_JS
from ..stealth.scripts.uach_spoof import get_js as UACH_SPOOF_JS
from ..stealth.scripts.storage_shim import JS as STORAGE_SHIM_JS
from ..stealth.scripts.iframe_harmonizer import JS as IFRAME_HARMONIZER_JS
from ..stealth.scripts.resize_observer_patch import JS as RESIZE_OBSERVER_PATCH_JS

class HardenedWebPage(QWebEnginePage):
    """
    Injects all anti-tracking and fingerprinting stealth JS scripts into every loaded page.
    """
    def __init__(self, parent=None, profile=None, canvas_seed=None):
        view = parent
        if profile is not None:
            try:
                super().__init__(profile, view)
            except TypeError:
                super().__init__(view)
        else:
            super().__init__(view)
        self._canvas_seed = canvas_seed or (secrets.randbits(32) & 0xFFFFFFFF)
        self._parent_view = view
        prof = self.profile()
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

    def inject_all_scripts(self):
        # Each line injects a pre-built JS string (or function with seed)
        self.inject_script(WEBRTC_BLOCK_JS, name="webrtc_block")
        self.inject_script(WEBRTC_SDP_SCRUB_JS, name="webrtc_sdp_scrub")
        self.inject_script(GEOLOCATION_BLOCK_JS, name="geolocation_block")
        self.inject_script(CANVAS_NOISE_JS(self._canvas_seed), name="canvas_noise")
        self.inject_script(WEBGL_SPOOF_JS, name="webgl_spoof")
        self.inject_script(AUDIO_NOISE_JS, name="audio_noise")
        self.inject_script(BATTERY_SPOOF_JS, name="battery_spoof")
        self.inject_script(FONT_SPOOF_JS, name="font_spoof")
        self.inject_script(TIMEZONE_SPOOF_JS, name="timezone_spoof")
        self.inject_script(UACH_SPOOF_JS(), name="uach_spoof")
        self.inject_script(STORAGE_SHIM_JS, name="storage_shim")
        self.inject_script(IFRAME_HARMONIZER_JS, name="iframe_harmonizer")
        self.inject_script(RESIZE_OBSERVER_PATCH_JS, name="resize_observer_patch")

    def acceptNavigationRequest(self, url, navtype, isMainFrame):
        if url.scheme() == "file":
            # Block file:// URLs for privacy
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Navigation blocked", "File URLs are blocked for privacy.")
            return False
        return super().acceptNavigationRequest(url, navtype, isMainFrame)

    def createWindow(self, _type):
        parent_view = getattr(self, "_parent_view", None)
        main_window = parent_view.window() if parent_view else None
        has_tabs = bool(main_window and hasattr(main_window, "_add_tab") and hasattr(main_window, "tabs"))
        view_parent = main_window if has_tabs else parent_view
        from PySide6.QtWebEngineWidgets import QWebEngineView
        view = QWebEngineView(view_parent)
        try:
            page = HardenedWebPage(view, self.profile())
        except TypeError:
            page = HardenedWebPage(view)
        view.setPage(page)
        page._parent_view = view
        page.fullScreenRequested.connect(
            view.window().handle_fullscreen
        )       
        if has_tabs:
            idx = main_window.tabs.addTab(view, "New Tab")
            main_window.tabs.setCurrentIndex(idx)
        else:
            view.show()
        if not hasattr(self, "_spawned_views"):
            self._spawned_views = []
        self._spawned_views.append(view)
        return page
