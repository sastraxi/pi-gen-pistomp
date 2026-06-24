#!/bin/bash
# Build pistomp-recovery .deb for arm64 Debian Trixie.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${ROOT_DIR}/scripts/build-common.sh"

PKG="pistomp-recovery"
VERSION="$(dpkg-parsechangelog -l "${SCRIPT_DIR}/debian/changelog" -S Version)"
UPSTREAM_DIR="${WORKDIR}/${PKG}-src"

cache_check

[ ! -d "${UPSTREAM_DIR}" ] && \
    git clone --branch "${PISTOMP_RECOVERY_BRANCH}" --depth 1 "${PISTOMP_RECOVERY_REPO}" "${UPSTREAM_DIR}"

# Install lg (build-time dep for liblgpio headers/library). In the full image
# build, lg.deb is already in CACHE_DIR. In CI (build-package-docker.sh or
# build-deb.yml), download it from GitHub Releases so we don't need the full
# cache to be populated.
if ! dpkg -s lg &>/dev/null; then
    if ls "${CACHE_DIR}/lg_"*"_arm64.deb" &>/dev/null; then
        dpkg -i "${CACHE_DIR}/lg_"*"_arm64.deb"
    else
        echo "==> lg not in cache; downloading latest from GitHub Releases..."
        LG_ASSET=$(gh release list --repo sastraxi/pi-gen-pistomp \
            --json tagName,assets --limit 100 \
            | jq -r '.[] | select(.tagName | startswith("debpkg/lg/")) \
                     | .assets[].browserDownloadUrl' \
            | grep 'lg_.*_arm64\.deb$' | head -1)
        if [[ -z "${LG_ASSET}" ]]; then
            echo "ERROR: lg.deb not found in GitHub Releases." >&2
            echo "Publish lg first: ./build-package-docker.sh lg, then create a release." >&2
            exit 1
        fi
        wget -q -P "${CACHE_DIR}" "${LG_ASSET}"
        dpkg -i "${CACHE_DIR}/lg_"*"_arm64.deb"
    fi
    apt-get install -f -y -qq
fi

cp -r "${SCRIPT_DIR}/debian" "${UPSTREAM_DIR}/"
cd "${UPSTREAM_DIR}"
dpkg-buildpackage -b -us -uc
move_to_cache
