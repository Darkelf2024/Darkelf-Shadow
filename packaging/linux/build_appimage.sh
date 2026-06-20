#!/usr/bin/env bash
#
# Build a Darkelf Shadow AppImage from a PyInstaller one-dir bundle.
#
#   packaging/linux/build_appimage.sh <version> <dist_dir> [out_dir]
#
# <dist_dir> must contain DarkelfShadow/DarkelfShadow (run PyInstaller with
# packaging/linux/darkelf.spec first). The result is a single self-contained
# Darkelf-Shadow-<version>-x86_64.AppImage that runs on most Linux distros
# without installation — chmod +x and double-click.
#
# appimagetool: set $APPIMAGETOOL to a binary, else one on PATH is used, else
# it is downloaded from the AppImage project. Runs with extract-and-run so it
# works in CI/containers without FUSE.

set -euo pipefail
VERSION="${1:?usage: build_appimage.sh <version> <dist_dir> [out_dir]}"
DIST_DIR="${2:?usage: build_appimage.sh <version> <dist_dir> [out_dir]}"
OUT_DIR="${3:-$PWD}"
ARCH="x86_64"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE="${DIST_DIR%/}/DarkelfShadow"

if [[ ! -x "${BUNDLE}/DarkelfShadow" ]]; then
    echo "error: ${BUNDLE}/DarkelfShadow not found (run PyInstaller first)" >&2
    exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT
APPDIR="${WORK}/DarkelfShadow.AppDir"
mkdir -p \
    "${APPDIR}/usr/bin" \
    "${APPDIR}/usr/share/applications" \
    "${APPDIR}/usr/share/icons/hicolor/256x256/apps"

# The whole PyInstaller bundle (DarkelfShadow + _internal/) lives in usr/bin so
# the executable still finds _internal/ next to it.
cp -r "${BUNDLE}/." "${APPDIR}/usr/bin/"

# Defensive: drop the bundled libgbm.so.1 so the app uses the host Mesa stack.
# Normally already excluded by packaging/linux/darkelf.spec (idempotent here).
rm -f "${APPDIR}/usr/bin/_internal/libgbm.so.1"

# Desktop entry — AppImage needs one at the AppDir root, and we also keep the
# canonical copy under usr/share/applications for desktop integration.
install -m 0644 "${SCRIPT_DIR}/darkelf-shadow.desktop" \
    "${APPDIR}/usr/share/applications/darkelf-shadow.desktop"
cp "${APPDIR}/usr/share/applications/darkelf-shadow.desktop" \
    "${APPDIR}/darkelf-shadow.desktop"

# Icon — must exist at the AppDir root named after the .desktop Icon= key
# (darkelf-shadow), plus the hicolor copy for integration.
ASSETS="${SCRIPT_DIR}/../../app/frontend/assets"
_icon="${ASSETS}/darkelf-mark-256.png"; [[ -f "$_icon" ]] || _icon="${ASSETS}/darkelf-256.png"
install -m 0644 "$_icon" "${APPDIR}/usr/share/icons/hicolor/256x256/apps/darkelf-shadow.png"
cp "$_icon" "${APPDIR}/darkelf-shadow.png"

# AppRun — the AppImage entry point. Mirrors the .deb launcher: software-GL
# escape hatch for headless/broken-driver machines (DARKELF_SOFTWARE_GL=1).
cat > "${APPDIR}/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
if [ -n "${DARKELF_SOFTWARE_GL:-}" ]; then
    export LIBGL_ALWAYS_SOFTWARE=1
    export QT_XCB_GL_INTEGRATION=none
    export QTWEBENGINE_CHROMIUM_FLAGS="${QTWEBENGINE_CHROMIUM_FLAGS:-} --disable-gpu"
fi
exec "${HERE}/usr/bin/DarkelfShadow" "$@"
EOF
chmod 0755 "${APPDIR}/AppRun"

# Resolve appimagetool: explicit > on PATH > download.
APPIMAGETOOL="${APPIMAGETOOL:-}"
if [[ -z "${APPIMAGETOOL}" ]]; then
    if command -v appimagetool >/dev/null 2>&1; then
        APPIMAGETOOL="appimagetool"
    else
        APPIMAGETOOL="${WORK}/appimagetool"
        URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
        echo "downloading appimagetool from ${URL}"
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL -o "${APPIMAGETOOL}" "${URL}"
        else
            wget -qO "${APPIMAGETOOL}" "${URL}"
        fi
        chmod +x "${APPIMAGETOOL}"
    fi
fi

mkdir -p "${OUT_DIR}"
OUT="${OUT_DIR}/Darkelf-Shadow-${VERSION}-${ARCH}.AppImage"

# extract-and-run lets appimagetool work without FUSE (CI/containers).
export APPIMAGE_EXTRACT_AND_RUN="${APPIMAGE_EXTRACT_AND_RUN:-1}"
ARCH="${ARCH}" "${APPIMAGETOOL}" "${APPDIR}" "${OUT}"
echo "built: ${OUT}"
