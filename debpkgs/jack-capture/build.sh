#!/bin/bash
# Build jack-capture .deb for arm64 Debian Trixie.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${ROOT_DIR}/scripts/build-common.sh"

PKG="jack-capture"
VERSION="$(dpkg-parsechangelog -l "${SCRIPT_DIR}/debian/changelog" -S Version)"
UPSTREAM_DIR="${WORKDIR}/${PKG}-src"

cache_check

[ ! -d "${UPSTREAM_DIR}" ] && \
    git clone --depth 100 "${JACK_CAPTURE_REPO}" "${UPSTREAM_DIR}"

# Ensure we are at the pinned commit (master containing post-0.9.73 fixes)
git -C "${UPSTREAM_DIR}" checkout "${JACK_CAPTURE_REF}"

cp -r "${SCRIPT_DIR}/debian" "${UPSTREAM_DIR}/"
cd "${UPSTREAM_DIR}"
dpkg-buildpackage -b -us -uc
move_to_cache
