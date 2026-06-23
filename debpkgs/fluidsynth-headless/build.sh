#!/bin/bash
# Build fluidsynth-headless .deb for arm64 Debian Trixie.
# Source is a tarball, not a git clone.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${ROOT_DIR}/scripts/build-common.sh"

PKG="fluidsynth-headless"
VERSION="${FLUIDSYNTH_VERSION}-1"
UPSTREAM_DIR="${WORKDIR}/fluidsynth-${FLUIDSYNTH_VERSION}"

cache_check

if [ ! -d "${UPSTREAM_DIR}" ]; then
    TARBALL="${WORKDIR}/fluidsynth-${FLUIDSYNTH_VERSION}.tar.gz"
    [ ! -f "${TARBALL}" ] && curl -fsSL -o "${TARBALL}" "${FLUIDSYNTH_URL}"
    tar xf "${TARBALL}" -C "$(dirname "${UPSTREAM_DIR}")"
fi

cp -r "${SCRIPT_DIR}/debian" "${UPSTREAM_DIR}/"
cd "${UPSTREAM_DIR}"
dpkg-buildpackage -b -us -uc
move_to_cache
