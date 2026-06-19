# darkelf.spec -- PyInstaller spec for Darkelf Shadow (Linux)
#
# Build from repo root:
#     pyinstaller packaging/linux/darkelf.spec --noconfirm
#
# Produces a one-dir bundle in dist/DarkelfShadow/ with the DarkelfShadow ELF,
# which packaging/linux/build_deb.sh then wraps into a .deb.
#
# This is the LINUX build and is deliberately separate from the Windows spec
# (packaging/windows/darkelf.spec): no .ico embedding (the desktop icon is
# installed by the .deb), and the stale bundled libgbm is dropped so the app
# uses the host Mesa stack (see below).

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules  # noqa: F401

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

# Drop the bundled libgbm.so.1. PyInstaller vendors the build host's copy, which
# on a newer end-user Mesa cannot load the system DRI drivers ("did not find
# extension DRI_Mesa version 1" / "EGL: Failed to initialize GBM device"), so
# GPU init fails and the window never appears. Removing it makes the dynamic
# loader fall back to the host's libgbm1 (a .deb runtime dependency), which
# matches the installed DRI drivers. build_deb.sh repeats this defensively.
a.binaries = [b for b in a.binaries
              if os.path.basename(b[0]).lower() != "libgbm.so.1"]

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
    console=False,           # GUI app, no controlling terminal
    disable_windowed_traceback=False,
    # No icon= on Linux: ELF carries no icon; the launcher icon is installed
    # by the .deb (usr/share/icons/hicolor/...) via build_deb.sh.
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="DarkelfShadow",
)
