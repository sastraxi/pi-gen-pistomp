#!/bin/bash
# Build sfizz-pistomp .deb for arm64 Debian Trixie.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${ROOT_DIR}/scripts/build-common.sh"

PKG="sfizz-pistomp"
VERSION="$(dpkg-parsechangelog -l "${SCRIPT_DIR}/debian/changelog" -S Version)"
UPSTREAM_DIR="${WORKDIR}/sfizz-ui-1.2.3"

cache_check

[ ! -d "${UPSTREAM_DIR}" ] && \
    git clone --branch "${SFIZZ_TAG}" --recurse-submodules "${SFIZZ_REPO}" "${UPSTREAM_DIR}"

cp -r "${SCRIPT_DIR}/debian" "${UPSTREAM_DIR}/"
cd "${UPSTREAM_DIR}"
dpkg-buildpackage -b -us -uc
move_to_cache
