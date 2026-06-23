#!/bin/bash
# Build libfluidsynth2-compat .deb — symlink shim, no compilation.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${ROOT_DIR}/scripts/build-common.sh"

PKG="libfluidsynth2-compat"
VERSION="$(grep '^Version:' "${SCRIPT_DIR}/debian/control" | awk '{print $2}')"

cache_check

DEB_DIR="${SCRIPT_DIR}/debian/${PKG}"
rm -rf "${DEB_DIR}"
mkdir -p "${DEB_DIR}/DEBIAN"

cp "${SCRIPT_DIR}/debian/control"  "${DEB_DIR}/DEBIAN/control"
cp "${SCRIPT_DIR}/debian/postinst" "${DEB_DIR}/DEBIAN/postinst"
chmod 755 "${DEB_DIR}/DEBIAN/postinst"

dpkg-deb --build --root-owner-group "${DEB_DIR}" "${CACHE_DIR}/${PKG}_${VERSION}_arm64.deb"

echo "==> Built ${PKG} → ${CACHE_DIR}/${PKG}_${VERSION}_arm64.deb"
