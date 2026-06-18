# darkelf.spec -- PyInstaller spec for Darkelf Shadow (Windows)
#
# Build from repo root:
#     pyinstaller packaging/windows/darkelf.spec --noconfirm
#
# Produces a one-dir bundle in dist/DarkelfShadow/ with DarkelfShadow.exe.

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# SPECPATH is already the directory containing this spec file.
ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
APP = os.path.join(ROOT, "app")

# Bundle the QML chrome (and any assets) as data, preserving layout.
datas = [
    (os.path.join(APP, "frontend", "qml"), os.path.join("frontend", "qml")),
]
_assets = os.path.join(APP, "frontend", "assets")
if os.path.isdir(_assets):
    datas.append((_assets, os.path.join("frontend", "assets")))

# Cutout mark = the app/taskbar icon (high contrast on dark taskbars).
_icon = os.path.join(APP, "frontend", "assets", "darkelf-mark.ico")
if not os.path.exists(_icon):
    _icon = os.path.join(APP, "frontend", "assets", "darkelf.ico")
_icon = _icon if os.path.exists(_icon) else None

hiddenimports = [
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineCore",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
    "PySide6.QtNetwork",
    "PySide6.QtOpenGL",
]
# Our own packages (followed automatically, but be explicit for safety).
hiddenimports += collect_submodules("backend")
hiddenimports += collect_submodules("frontend")

a = Analysis(
    [os.path.join(APP, "app.py")],
    pathex=[APP],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "PySide6.QtWebEngineWidgets"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DarkelfShadow",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # GUI app, no console window
    disable_windowed_traceback=False,
    icon=_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="DarkelfShadow",
)
