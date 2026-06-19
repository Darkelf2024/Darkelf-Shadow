# frontend/controller.py
#
# The single QObject bridge between the QML chrome and the hardened backend.
# QML never imports backend logic directly -- it calls slots / reads properties
# on this controller.

import json
import os
import re
import shutil

from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer, QUrl
from urllib.parse import quote_plus, urlsplit

_DARKELF_DIR = os.path.join(os.path.expanduser("~"), ".darkelf")
_BOOKMARKS_PATH = os.path.join(_DARKELF_DIR, "bookmarks.json")
_PREFS_PATH = os.path.join(_DARKELF_DIR, "prefs.json")
_MAX_BG_BYTES = 12 * 1024 * 1024  # cap imported background image size

from backend.utils import sanitize_url_clearurls, _randomized_filename, DUCK_LITE_HTTPS

_SCHEME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*://')
_DOMAIN_RE = re.compile(r'^[\w.-]+\.[A-Za-z]{2,}(/|$)')
_IP_LOCAL_RE = re.compile(r'^(localhost|(?:\d{1,3}\.){3}\d{1,3})(:\d+)?(/|$)?$')


# Homepage background presets (CSS `background` shorthand). Accent-aware.
BACKGROUND_IDS = ["aurora", "graded", "matrix", "circuit", "nebula", "void"]


def _bg_css(choice: str, accent: str, data_uri: str | None) -> str:
    if choice == "custom" and data_uri:
        return f'#06070b url("{data_uri}") center/cover no-repeat fixed'
    presets = {
        "aurora": (
            f"radial-gradient(1100px 560px at 18% -12%, color-mix(in srgb, {accent} 32%, transparent), transparent 60%),"
            f"radial-gradient(900px 540px at 118% 8%, color-mix(in srgb, {accent} 40%, transparent), transparent 60%),"
            "#0a0b10"
        ),
        "graded": "linear-gradient(135deg,#05060a 0%,#13151f 48%,#0a0b10 100%)",
        "matrix": (
            "linear-gradient(rgba(3,8,4,0.86),rgba(3,8,5,0.94)),"
            "repeating-linear-gradient(90deg, rgba(45,255,140,0.06) 0 1px, transparent 1px 24px),"
            "repeating-linear-gradient(0deg, rgba(45,255,140,0.06) 0 1px, transparent 1px 24px),"
            "#04070a"
        ),
        "circuit": (
            f"repeating-linear-gradient(0deg, color-mix(in srgb, {accent} 9%, transparent) 0 1px, transparent 1px 30px),"
            f"repeating-linear-gradient(90deg, color-mix(in srgb, {accent} 9%, transparent) 0 1px, transparent 1px 30px),"
            "#07080e"
        ),
        "nebula": (
            "radial-gradient(820px 520px at 18% 8%, rgba(168,85,247,0.26), transparent 60%),"
            "radial-gradient(720px 520px at 86% 18%, rgba(64,169,255,0.18), transparent 60%),"
            "radial-gradient(760px 620px at 50% 116%, rgba(247,89,171,0.16), transparent 60%),"
            "#07080e"
        ),
        "void": "#06070b",
    }
    return presets.get(choice, presets["aurora"])


def _homepage_html(accent: str, bg_css: str) -> str:
    return """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>Darkelf Shadow</title>
<style>
:root { --accent: %ACCENT%; --bg:#0a0b10; }
* { box-sizing:border-box; }
html,body { height:100%; margin:0; }
body {
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Arial;
  background: %BG%;
  color:#eef2f6; display:flex; flex-direction:column;
  justify-content:center; align-items:center; gap:26px;
}
.brand { font-weight:800; font-size:3.4rem; letter-spacing:.5px;
  display:flex; align-items:center; gap:14px; }
.dot { width:18px; height:18px; border-radius:50%;
  background:var(--accent);
  box-shadow:0 0 14px color-mix(in srgb, var(--accent) 85%, transparent); }
.sub { color:#aab3c0; font-size:.95rem; margin-top:-12px; }
form { width:min(620px, 86vw); }
input {
  width:100%; padding:15px 18px; border-radius:14px;
  border:1px solid color-mix(in srgb, var(--accent) 45%, #1b1f27);
  background:#0e1017; color:#eef2f6; font-size:1.05rem; outline:none;
}
input:focus { border-color:var(--accent);
  box-shadow:0 0 0 3px color-mix(in srgb, var(--accent) 25%, transparent); }
.tags { display:flex; gap:10px; flex-wrap:wrap; justify-content:center;
  color:#8b93a1; font-size:.8rem; }
.tag { padding:5px 11px; border-radius:999px;
  border:1px solid #1b1f27; background:#0d0f15; }
</style></head>
<body>
  <div class="brand"><span class="dot"></span>Darkelf Shadow</div>
  <div class="sub">Ephemeral &middot; Hardened &middot; In-memory</div>
  <form method="GET" action="https://duckduckgo.com/lite/">
    <input name="q" autofocus autocomplete="off" spellcheck="false"
           placeholder="Search privately, or type a URL in the bar above" />
  </form>
  <div class="tags">
    <span class="tag">No persistence</span>
    <span class="tag">Fingerprint defense</span>
    <span class="tag">Tracker filtering</span>
    <span class="tag">HTTPS upgrade</span>
  </div>
</body></html>""".replace("%ACCENT%", accent).replace("%BG%", bg_css)


class DarkelfController(QObject):

    accentColorChanged = Signal()
    homepageHtmlChanged = Signal()
    miniaiStatusChanged = Signal(str)   # "STANDBY" | "LOCKDOWN" | "PANIC"
    bookmarksChanged = Signal()
    backgroundChanged = Signal()
    quitRequested = Signal()

    def __init__(self, app, engine, parent=None):
        super().__init__(parent)
        self._app = app
        self._engine = engine            # backend.profile.DarkelfEngine
        self._accent = "#A855F7"
        self._download_dir = None
        self._last_status = "STANDBY"
        self._bookmarks = self._load_bookmarks()
        self._logged_events = 0

        # Homepage background preference.
        prefs = self._load_prefs()
        self._bg = prefs.get("background", "aurora")
        self._bg_custom_path = prefs.get("custom_path")
        self._bg_data_uri = None
        if self._bg == "custom" and self._bg_custom_path:
            self._encode_custom_bg(self._bg_custom_path)

        # Secure downloads: randomized filename into a lazily-created dir.
        self._engine.profile.downloadRequested.connect(self._on_download)

        # Wipe download traces + report on exit.
        app.aboutToQuit.connect(self._wipe_download_traces)

        # Poll the sentinel: drive its timeout auto-release and surface status.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    # --- properties --------------------------------------------------------

    def _get_accent(self):
        return self._accent

    def _set_accent(self, value):
        if value and value != self._accent:
            self._accent = value
            self.accentColorChanged.emit()
            self.homepageHtmlChanged.emit()

    accentColor = Property(str, _get_accent, _set_accent, notify=accentColorChanged)

    def _get_homepage(self):
        return _homepage_html(self._accent, _bg_css(self._bg, self._accent, self._bg_data_uri))

    homepageHtml = Property(str, _get_homepage, notify=homepageHtmlChanged)

    def _get_background(self):
        return self._bg

    backgroundChoice = Property(str, _get_background, notify=backgroundChanged)

    @Slot(str)
    def setBackground(self, choice: str):
        self._bg = choice or "aurora"
        self._save_prefs()
        self.backgroundChanged.emit()
        self.homepageHtmlChanged.emit()

    @Slot(str)
    def importBackgroundFile(self, file_url: str):
        path = QUrl(file_url).toLocalFile() if str(file_url).startswith("file:") else str(file_url)
        if self._encode_custom_bg(path):
            self._bg = "custom"
            self._bg_custom_path = path
            self._save_prefs()
            self.backgroundChanged.emit()
            self.homepageHtmlChanged.emit()

    def _get_version(self):
        return "5.0.0"  # x-release-please-version

    appVersion = Property(str, _get_version, constant=True)

    # --- navigation helpers (called from QML address bar) ------------------

    @Slot(str, result=str)
    def resolveInput(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        if _SCHEME_RE.match(text):
            url = text
        elif _DOMAIN_RE.match(text) or _IP_LOCAL_RE.match(text):
            url = "https://" + text
        else:
            url = DUCK_LITE_HTTPS + "?q=" + quote_plus(text)
        return sanitize_url_clearurls(url)

    @Slot(str, result=str)
    def cssForHost(self, host: str) -> str:
        try:
            return self._engine.engine.css_for_host((host or "").lower())
        except Exception as e:
            print("[Darkelf] cssForHost error:", e)
            return ""

    @Slot(str, result=str)
    def shortLabel(self, url: str) -> str:
        try:
            q = QUrl(url)
            host = q.host()
            if host:
                return host[:28]
            s = q.toString()
            return (s[:24] + "...") if len(s) > 27 else (s or "New Tab")
        except Exception:
            return "New Tab"

    # --- privacy actions ---------------------------------------------------

    @Slot()
    def nuke(self):
        self._engine.wipe()
        self.quitRequested.emit()

    @Slot(result=str)
    def miniaiReport(self) -> str:
        try:
            return self._engine.mini_ai.get_threat_report()
        except Exception as e:
            return f"Report unavailable: {e}"

    @Slot(result="QVariantMap")
    def miniaiStats(self):
        """Structured stats for the dashboard UI (instead of the ASCII report)."""
        try:
            s = self._engine.mini_ai.get_statistics()
            recent = []
            for e in s.get("recent_threats", [])[-6:]:
                recent.append({
                    "when": e.get("datetime", ""),
                    "risk": e.get("risk_level", "low"),
                    "threats": ", ".join((e.get("threats") or [])[:3]),
                })
            return {
                "status": self._last_status,
                "uptimeMin": round(s.get("uptime_seconds", 0) / 60.0, 1),
                "events": s.get("total_events", 0),
                "domains": s.get("unique_domains", 0),
                "score": s.get("threat_score", 0),
                "threats": s.get("threats", {}),
                "fp": s.get("fingerprinting_apis", {}),
                "recent": recent,
            }
        except Exception as e:
            print("[Darkelf] miniaiStats error:", e)
            return {"status": "STANDBY", "uptimeMin": 0, "events": 0, "domains": 0,
                    "score": 0, "threats": {}, "fp": {}, "recent": []}

    @Slot(result=str)
    def miniaiStatus(self) -> str:
        return self._last_status

    @Slot(result=int)
    def threatScore(self) -> int:
        try:
            return int(self._engine.mini_ai.get_statistics().get("threat_score", 0))
        except Exception:
            return 0

    # --- bookmarks ---------------------------------------------------------
    # Bookmarks are the one intentional on-disk artifact: explicit user data,
    # stored unencrypted in ~/.darkelf/bookmarks.json. They are never sent
    # anywhere and can be cleared by deleting that file.

    def _load_bookmarks(self) -> list:
        try:
            with open(_BOOKMARKS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [b for b in data if isinstance(b, dict) and b.get("url")]
        except Exception:
            pass
        return []

    def _save_bookmarks(self) -> None:
        try:
            os.makedirs(_DARKELF_DIR, mode=0o700, exist_ok=True)
            with open(_BOOKMARKS_PATH, "w", encoding="utf-8") as f:
                json.dump(self._bookmarks, f, indent=2)
        except Exception as e:
            print("[Darkelf] bookmark save error:", e)

    @Slot(result="QVariantList")
    def getBookmarks(self):
        return list(self._bookmarks)

    @Slot(str, str)
    def addBookmark(self, title: str, url: str):
        url = (url or "").strip()
        if not url or urlsplit(url).hostname == "darkelf.home":
            return
        if any(b.get("url") == url for b in self._bookmarks):
            return
        title = (title or url)[:80]
        self._bookmarks.append({"title": title, "url": url})
        self._save_bookmarks()
        self.bookmarksChanged.emit()

    @Slot(str)
    def removeBookmark(self, url: str):
        url = (url or "").strip()
        before = len(self._bookmarks)
        self._bookmarks = [b for b in self._bookmarks if b.get("url") != url]
        if len(self._bookmarks) != before:
            self._save_bookmarks()
            self.bookmarksChanged.emit()

    @Slot(str, str)
    def toggleBookmark(self, title: str, url: str):
        if self.isBookmarked(url):
            self.removeBookmark(url)
        else:
            self.addBookmark(title, url)

    @Slot(str, result=bool)
    def isBookmarked(self, url: str) -> bool:
        url = (url or "").strip()
        return any(b.get("url") == url for b in self._bookmarks)

    # --- preferences / background -----------------------------------------

    def _load_prefs(self) -> dict:
        try:
            with open(_PREFS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_prefs(self) -> None:
        try:
            os.makedirs(_DARKELF_DIR, mode=0o700, exist_ok=True)
            data = {"background": self._bg}
            if self._bg_custom_path:
                data["custom_path"] = self._bg_custom_path
            with open(_PREFS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print("[Darkelf] prefs save error:", e)

    def _encode_custom_bg(self, path: str) -> bool:
        """Read an image and cache it as a base64 data URI for the homepage."""
        import base64
        try:
            size = os.path.getsize(path)
            if size > _MAX_BG_BYTES:
                print("[Darkelf] background image too large (>12MB):", path)
                return False
            with open(path, "rb") as f:
                raw = f.read()
        except Exception as e:
            print("[Darkelf] background import failed:", e)
            return False
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        mime = {
            "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "gif": "image/gif", "bmp": "image/bmp",
        }.get(ext, "image/png")
        self._bg_data_uri = "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode("ascii"))
        return True

    # --- internals ---------------------------------------------------------

    def _tick(self):
        ai = self._engine.mini_ai
        try:
            ai.check_lockdown_timeout()
        except Exception:
            pass

        # Log any new threat-flagged events to the session log (for feature testing).
        try:
            events = list(ai.events)
            new = events[self._logged_events:]
            for e in new:
                threats = e.get("threats") or []
                if threats:
                    print("[EVENT] %-8s %s  %s" % (
                        e.get("risk_level", "low").upper(),
                        ",".join(threats[:4]),
                        (e.get("url", "") or "")[:90],
                    ))
            self._logged_events = len(events)
        except Exception:
            pass
        if getattr(ai, "panic_mode_active", False):
            status = "PANIC"
        elif getattr(ai, "lockdown_active", False):
            status = "LOCKDOWN"
        else:
            status = "STANDBY"
        if status != self._last_status:
            self._last_status = status
            self.miniaiStatusChanged.emit(status)

    def _ensure_download_dir(self) -> str:
        base = os.path.join(os.path.expanduser("~"), "Desktop", "Darkelf Library")
        d = os.path.join(base, "Darkelf Temp Folder")
        os.makedirs(d, mode=0o700, exist_ok=True)
        try:
            os.chmod(d, 0o700)
        except Exception:
            pass
        self._download_dir = d
        return d

    def _on_download(self, item):
        try:
            fname = os.path.basename(_randomized_filename(item.downloadFileName()))
            d = self._ensure_download_dir()
            item.setDownloadDirectory(d)
            item.setDownloadFileName(fname)
            item.accept()
        except Exception as e:
            print("[Darkelf] download error:", e)

    def _wipe_download_traces(self):
        try:
            self._engine.shutdown()
        except Exception:
            pass
        try:
            if self._download_dir and os.path.isdir(self._download_dir):
                shutil.rmtree(self._download_dir, ignore_errors=True)
        except Exception as e:
            print("[Darkelf] wipe traces error:", e)
