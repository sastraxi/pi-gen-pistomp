#!/usr/bin/env bash
# Build a single debpkgs/<pkg> inside the pi-gen Docker container.
# Usage: ./build-package-docker.sh <pkg>
#   e.g. ./build-package-docker.sh jack2-pistomp
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <pkg>"
    echo "  e.g. $0 jack2-pistomp"
    exit 1
fi

PKG="$1"
DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"

if [ ! -d "${DIR}/debpkgs/${PKG}" ]; then
    echo "Error: debpkgs/${PKG} not found."
    exit 1
fi

if [ ! -f "${DIR}/debpkgs/${PKG}/build.sh" ]; then
    echo "Error: debpkgs/${PKG}/build.sh not found (package may use Phase 2 download)."
    exit 1
fi

DOCKER=${DOCKER:-docker}

# Ensure the pi-gen image exists
if ! ${DOCKER} image inspect pi-gen &>/dev/null; then
    echo "Building pi-gen Docker image..."
    ${DOCKER} build -t pi-gen "${DIR}"
fi

# Mount cache/ at /pistomp-cache (same as build-docker.sh).
# Repo is mounted rw because lcd-splash and libfluidsynth2-compat write into
# debpkgs/<pkg>/debian/ as their dpkg-deb staging tree.
echo "==> Building ${PKG} in Docker container..."
${DOCKER} run --rm -it \
    --volume "${DIR}/cache":/pistomp-cache:rw \
    --volume "${DIR}":/pistomp:rw \
    -e "CACHE_DIR=/pistomp-cache" \
    -e "WORKDIR=/tmp/build-pkg" \
    -e "FORCE_REBUILD=${FORCE_REBUILD:-0}" \
    -e "UV_CACHE_DIR=/pistomp-cache/uv-cache" \
    -e "UV_PYTHON_INSTALL_DIR=/pistomp-cache/uv-python" \
    -e "PIP_CACHE_DIR=/pistomp-cache/pip-cache" \
    pi-gen \
    bash "/pistomp/debpkgs/${PKG}/build.sh"
