#!/usr/bin/env bash

set -euo pipefail
VERSION="${1:?usage: build_deb.sh <version> <dist_dir> [out_dir]}"
DIST_DIR="${2:?usage: build_deb.sh <version> <dist_dir> [out_dir]}"
OUT_DIR="${3:-$PWD}"
ARCH="amd64"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE="${DIST_DIR%/}/DarkelfShadow"

if [[ ! -x "${BUNDLE}/DarkelfShadow" ]]; then
    echo "error: ${BUNDLE}/DarkelfShadow not found (run PyInstaller first)" >&2
    exit 1
fi

PKG="darkelf-shadow_${VERSION}_${ARCH}"
WORK="$(mktemp -d)"
ROOT="${WORK}/${PKG}"
mkdir -p \
    "${ROOT}/opt/darkelf-shadow" \
    "${ROOT}/usr/bin" \
    "${ROOT}/usr/share/applications" \
    "${ROOT}/usr/share/icons/hicolor/256x256/apps" \
    "${ROOT}/usr/share/icons/hicolor/128x128/apps" \
    "${ROOT}/DEBIAN"

cp -r "${BUNDLE}/." "${ROOT}/opt/darkelf-shadow/"

cat > "${ROOT}/usr/bin/darkelf-shadow" <<'EOF'
#!/bin/sh
exec /opt/darkelf-shadow/DarkelfShadow "$@"
EOF
chmod 0755 "${ROOT}/usr/bin/darkelf-shadow"
install -m 0644 "${SCRIPT_DIR}/darkelf-shadow.desktop" \
    "${ROOT}/usr/share/applications/darkelf-shadow.desktop"

# Icons (resolve the Icon=darkelf-shadow name in the .desktop entry).
# Prefer the cutout mark; fall back to the tiled logo.
ASSETS="${ROOT_SRC:-${SCRIPT_DIR}/../../app/frontend/assets}"
_icon256="${ASSETS}/darkelf-mark-256.png"; [[ -f "$_icon256" ]] || _icon256="${ASSETS}/darkelf-256.png"
_icon128="${ASSETS}/darkelf-mark-128.png"; [[ -f "$_icon128" ]] || _icon128="${ASSETS}/darkelf-128.png"
if [[ -f "$_icon256" ]]; then
    install -m 0644 "$_icon256" "${ROOT}/usr/share/icons/hicolor/256x256/apps/darkelf-shadow.png"
fi
if [[ -f "$_icon128" ]]; then
    install -m 0644 "$_icon128" "${ROOT}/usr/share/icons/hicolor/128x128/apps/darkelf-shadow.png"
fi

# Installed size (KiB)
INSTALLED_SIZE="$(du -sk "${ROOT}/opt" | cut -f1)"

cat > "${ROOT}/DEBIAN/control" <<EOF
Package: darkelf-shadow
Version: ${VERSION}
Section: web
Priority: optional
Architecture: ${ARCH}
Installed-Size: ${INSTALLED_SIZE}
Depends: libnss3, libnspr4, libxcomposite1, libxdamage1, libxrandr2, libxkbcommon0, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libxcb-shape0, libgbm1, libegl1, libgl1, libasound2 | libasound2t64, fonts-liberation
Maintainer: Darkelf Project <noreply@darkelf.invalid>
Description: Hardened ephemeral privacy browser
 Darkelf Shadow is a defense-in-depth, privacy-hardened web browser built on
 Qt WebEngine. It runs entirely in-memory (off-the-record), blocks trackers,
 upgrades HTTP to HTTPS, and applies on-device fingerprint defenses.
EOF
chmod 0755 "${ROOT}/DEBIAN"

dpkg-deb --build --root-owner-group "${ROOT}" "${OUT_DIR}/${PKG}.deb"
echo "built: ${OUT_DIR}/${PKG}.deb"
