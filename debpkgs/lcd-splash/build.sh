#!/bin/bash
# Build lcd-splash .deb for arm64 Debian Trixie — builds from C source.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PKG="lcd-splash"
VERSION="1.0-2"
CACHE_DIR="${CACHE_DIR:-${ROOT_DIR}/cache}"
SRC_DIR="${SCRIPT_DIR}/src"

mkdir -p "${CACHE_DIR}"

if ls "${CACHE_DIR}/${PKG}_${VERSION}"*_arm64.deb &>/dev/null && [[ -z "${FORCE_REBUILD:-}" ]]; then
    echo "==> ${PKG} already in cache, skipping."
    exit 0
fi

# Stage files into the debian package tree
DEB_DIR="${SCRIPT_DIR}/debian/${PKG}"
rm -rf "${DEB_DIR}"
mkdir -p "${DEB_DIR}/DEBIAN"
mkdir -p "${DEB_DIR}/usr/bin"
mkdir -p "${DEB_DIR}/usr/share/pistomp"

# DEBIAN/control
cp "${SCRIPT_DIR}/debian/control" "${DEB_DIR}/DEBIAN/control"

# Generate font.h from Terminus Bold 22px console font
python3 "${SRC_DIR}/gen-font-h.py" \
    /usr/share/consolefonts/Lat15-TerminusBold22x11.psf.gz > "${SRC_DIR}/font.h"

# Compile
gcc -O2 -Wall -Wextra \
    -o "${DEB_DIR}/usr/bin/lcd-splash" "${SRC_DIR}/lcd-splash.c" \
    -I"${SRC_DIR}" \
    -llgpio

# Splash image
cp "${ROOT_DIR}/stage2/05-pistomp/files/splash.rgb565" \
    "${DEB_DIR}/usr/share/pistomp/splash.rgb565"

# Build the .deb
dpkg-deb --build --root-owner-group "${DEB_DIR}" "${CACHE_DIR}/${PKG}_${VERSION}_arm64.deb"

echo "==> Built ${PKG} → ${CACHE_DIR}"
