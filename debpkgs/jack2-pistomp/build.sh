#!/bin/bash
# Build jack2-pistomp .deb for arm64 Debian Trixie.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${ROOT_DIR}/scripts/build-common.sh"

PKG="jack2-pistomp"
VERSION="${JACK2_TAG#v}"        # strip leading v → 1.9.22
UPSTREAM_DIR="${WORKDIR}/${PKG}-src"

cache_check

[ ! -d "${UPSTREAM_DIR}" ] && \
    git clone --branch "${JACK2_TAG}" --depth 1 "${JACK2_REPO}" "${UPSTREAM_DIR}"

cp -r "${SCRIPT_DIR}/debian" "${UPSTREAM_DIR}/"
cd "${UPSTREAM_DIR}"
dpkg-buildpackage -b -us -uc
move_to_cache
