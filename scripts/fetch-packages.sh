#!/bin/bash
# fetch-packages — build or download .deb packages for the image.
#
# Phase 1 (monorepo): for each package with a debpkgs/<pkg>/build.sh, run it
# to produce .deb files in CACHE_DIR.
#
# Phase 2 (external repo): TODO — download from _DEB_REPO/_DEB_VERSION instead.
#
# Usage:
#   source config.sh
#   CACHE_DIR=/path/to/cache ./scripts/fetch-packages.sh [pkg1 pkg2 ...]
#
# If no packages are named, all packages under debpkgs/ are processed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source config.sh (idempotent if already sourced)
# shellcheck source=../config.sh
source "${ROOT_DIR}/config.sh"

CACHE_DIR="${CACHE_DIR:-${ROOT_DIR}/cache}"
FORCE_REBUILD="${FORCE_REBUILD:-}"
WORKDIR="${WORKDIR:-/tmp}"

mkdir -p "${CACHE_DIR}"

# Determine which packages to process
if [[ $# -gt 0 ]]; then
    PACKAGES=("$@")
else
    # Auto-discover: every subdirectory under debpkgs/ that has a build.sh
    PACKAGES=()
    for d in "${ROOT_DIR}/debpkgs/"*/; do
        pkg="$(basename "$d")"
        [[ "$pkg" == "template" ]] && continue
        [[ -f "${d}/build.sh" ]] && PACKAGES+=("$pkg")
    done
fi

for PKG in "${PACKAGES[@]}"; do
    BUILD_SCRIPT="${ROOT_DIR}/debpkgs/${PKG}/build.sh"

    if [[ -f "${BUILD_SCRIPT}" ]]; then
        # Phase 1: local build
        echo "==> fetch-packages: building ${PKG}..."
        CACHE_DIR="${CACHE_DIR}" \
        FORCE_REBUILD="${FORCE_REBUILD}" \
        WORKDIR="${WORKDIR}" \
            bash "${BUILD_SCRIPT}"
    else
        # Phase 2: download from release
        # TODO: implement download from _DEB_REPO/_DEB_VERSION
        echo "==> fetch-packages: no build.sh for ${PKG}, skipping (phase 2 not yet implemented)."
    fi
done

echo "==> fetch-packages: done.  Cached .deb files in ${CACHE_DIR}:"
ls -1 "${CACHE_DIR}"/*.deb 2>/dev/null || echo "(none)"
