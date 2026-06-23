#!/bin/bash
# Sourced by debpkgs/*/build.sh. Caller must set SCRIPT_DIR and ROOT_DIR first.
# shellcheck source=../config.sh
source "${ROOT_DIR}/config.sh"

CACHE_DIR="${CACHE_DIR:-${ROOT_DIR}/cache}"
WORKDIR="${WORKDIR:-/tmp}"

mkdir -p "${CACHE_DIR}"

# Exit 0 if the versioned .deb is already in cache and FORCE_REBUILD != 1.
# Caller must set PKG and VERSION before calling.
cache_check() {
    if ls "${CACHE_DIR}/${PKG}_${VERSION}"*_arm64.deb &>/dev/null \
            && [[ "${FORCE_REBUILD:-0}" != "1" ]]; then
        echo "==> ${PKG} already in cache, skipping."
        exit 0
    fi
}

# Move built .deb(s) from a parent directory into CACHE_DIR.
# Usage: move_to_cache [parent_dir]   (default: parent of UPSTREAM_DIR)
move_to_cache() {
    local search_dir="${1:-$(dirname "${UPSTREAM_DIR}")}"
    find "${search_dir}" -maxdepth 1 -name "${PKG}_*.deb" -exec mv {} "${CACHE_DIR}/" \;
    local latest
    latest="$(ls -t "${CACHE_DIR}/${PKG}_"*"_arm64.deb" 2>/dev/null | head -1)"
    if [[ -n "${latest}" ]]; then
        ln -sf "$(basename "${latest}")" "${CACHE_DIR}/${PKG}.deb"
    fi
    echo "==> Built ${PKG} → ${CACHE_DIR}"
}
