#!/bin/bash
# Build lg .deb for arm64 Debian Trixie.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PKG="lg"
VERSION="0.2.2-1"
CACHE_DIR="${CACHE_DIR:-${ROOT_DIR}/cache}"
UPSTREAM_DIR="${WORKDIR:-/tmp}/${PKG}-src"

mkdir -p "${CACHE_DIR}"

if ls "${CACHE_DIR}/${PKG}_${VERSION}"*_arm64.deb &>/dev/null && [[ -z "${FORCE_REBUILD:-}" ]]; then
    echo "==> ${PKG} already in cache, skipping."
    exit 0
fi

[ ! -d "${UPSTREAM_DIR}" ] && \
    git clone --depth 1 --branch v0.2.2 \
        https://github.com/joan2937/lg.git "${UPSTREAM_DIR}"

cp -r "${SCRIPT_DIR}/debian" "${UPSTREAM_DIR}/"
cd "${UPSTREAM_DIR}"
dpkg-buildpackage -b -us -uc

find "$(dirname "${UPSTREAM_DIR}")" -maxdepth 1 -name "${PKG}_*.deb" \
    -exec mv {} "${CACHE_DIR}/" \;

echo "==> Built ${PKG} → ${CACHE_DIR}"
