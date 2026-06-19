# app.py  --  Darkelf Shadow entry point
#
# One process, internal frontend/backend split:
#   backend.profile.DarkelfEngine  -> hardened off-the-record web engine
#   frontend.controller            -> QObject bridge exposed to QML
#   frontend/qml/Main.qml          -> the chrome (Brave-style)

import os
import sys

# A windowed (no-console) PyInstaller build sets sys.stdout/sys.stderr to None.
# Our modules print() heavily, so guard against that first or the app crashes
# on the first log line when double-clicked from Explorer.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Windows consoles default to cp1252, which can't encode the box-drawing /
# emoji characters used in logs and the MiniAI report. Force UTF-8 so logging
# never raises UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _open_session_log():
    """Tee stdout/stderr to a per-session log file under ~/.darkelf/logs.

    Dev/test only: a zero-trace browser must not write logs to disk by default.
    Enabled solely when DARKELF_DEV=1.
    """
    if os.environ.get("DARKELF_DEV") != "1":
        return None
    import time
    log_dir = os.path.join(os.path.expanduser("~"), ".darkelf", "logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        return None
    path = os.path.join(log_dir, time.strftime("darkelf-%Y%m%d-%H%M%S.log"))
    try:
        f = open(path, "w", encoding="utf-8", buffering=1)  # line-buffered
    except Exception:
        return None

    class _Tee:
        def __init__(self, *streams):
            self._streams = [s for s in streams if s]
        def write(self, data):
            for s in self._streams:
                try:
                    s.write(data)
                    s.flush()
                except Exception:
                    pass
            return len(data)
        def flush(self):
            for s in self._streams:
                try:
                    s.flush()
                except Exception:
                    pass

    sys.stdout = _Tee(sys.stdout, f)
    sys.stderr = _Tee(sys.stderr, f)
    return path


_LOG_PATH = _open_session_log()

# Chromium flags MUST be set before the Qt application is constructed.
from backend.flags import apply_chromium_flags
apply_chromium_flags()

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWebEngineQuick import QtWebEngineQuick

from backend.profile import DarkelfEngine
from frontend.controller import DarkelfController


def _resource_dir() -> str:
    # Works both in dev and inside a PyInstaller bundle.
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    # Windows: give the process an explicit AppUserModelID so the taskbar groups
    # it under our own icon instead of python.exe (matters for source runs).
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Darkelf.Shadow")
        except Exception:
            pass

    QtWebEngineQuick.initialize()

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Darkelf Shadow")
    app.setOrganizationName("Darkelf")
    app.setApplicationDisplayName("Darkelf Shadow")

    # Prefer the cutout mark (best contrast on a dark taskbar); fall back to the
    # tiled logo. The .ico carries every size for crisp small renders.
    assets = os.path.join(_resource_dir(), "frontend", "assets")
    for _name in ("darkelf-mark.ico", "darkelf-mark.png", "darkelf.ico", "darkelf.png"):
        _p = os.path.join(assets, _name)
        if os.path.exists(_p):
            app.setWindowIcon(QIcon(_p))
            break

    # Backend: hardened engine (loads filter lists on startup).
    # DARKELF_NO_FILTERS=1 skips the network fetch (useful for smoke tests).
    load_filters = os.environ.get("DARKELF_NO_FILTERS") != "1"
    engine = DarkelfEngine(parent=app, load_filters=load_filters)
    if _LOG_PATH:
        print("Session log:", _LOG_PATH)
    print("OffTheRecord:", engine.profile.isOffTheRecord())
    if engine.filters_ready.is_set():
        print("Loaded network rules:", len(engine.engine.network_rules))
    else:
        print("Filters: loading in background...")

    # Bridge.
    controller = DarkelfController(app, engine)

    qml_engine = QQmlApplicationEngine()
    ctx = qml_engine.rootContext()
    ctx.setContextProperty("darkelfProfile", engine.profile)
    ctx.setContextProperty("darkelf", controller)

    qml_path = os.path.join(_resource_dir(), "frontend", "qml", "Main.qml")
    qml_engine.load(QUrl.fromLocalFile(qml_path))

    if not qml_engine.rootObjects():
        print("FATAL: failed to load QML:", qml_path)
        return 1

    # DARKELF_AUTOQUIT=<ms> exits after a delay (smoke testing).
    autoquit = os.environ.get("DARKELF_AUTOQUIT")
    if autoquit:
        from PySide6.QtCore import QTimer
        print("BOOT OK: QML chrome loaded")
        QTimer.singleShot(int(autoquit), app.quit)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
