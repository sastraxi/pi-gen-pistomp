#!/bin/bash
# Build fluidsynth-headless .deb for arm64 Debian Trixie.
# Source is a tarball, not a git clone.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck source=../../config.sh
source "${ROOT_DIR}/config.sh"

PKG="fluidsynth-headless"
VERSION="${FLUIDSYNTH_VERSION}-1"
CACHE_DIR="${CACHE_DIR:-${ROOT_DIR}/cache}"
UPSTREAM_DIR="${WORKDIR:-/tmp}/fluidsynth-${FLUIDSYNTH_VERSION}"

mkdir -p "${CACHE_DIR}"

# Skip if already cached
if ls "${CACHE_DIR}/${PKG}_${VERSION}"*_arm64.deb &>/dev/null && [[ -z "${FORCE_REBUILD:-}" ]]; then
    echo "==> ${PKG} already in cache, skipping."
    exit 0
fi

# Download and extract tarball if not already present
if [ ! -d "${UPSTREAM_DIR}" ]; then
    TARBALL="${WORKDIR:-/tmp}/fluidsynth-${FLUIDSYNTH_VERSION}.tar.gz"
    if [ ! -f "${TARBALL}" ]; then
        curl -fsSL -o "${TARBALL}" "${FLUIDSYNTH_URL}"
    fi
    tar xf "${TARBALL}" -C "$(dirname "${UPSTREAM_DIR}")"
fi

cp -r "${SCRIPT_DIR}/debian" "${UPSTREAM_DIR}/"
cd "${UPSTREAM_DIR}"
dpkg-buildpackage -b -us -uc

# Move output debs to cache
find "$(dirname "${UPSTREAM_DIR}")" -maxdepth 1 -name "${PKG}_*.deb" \
    -exec mv {} "${CACHE_DIR}/" \;

echo "==> Built ${PKG} → ${CACHE_DIR}"
