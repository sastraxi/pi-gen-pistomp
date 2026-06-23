#!/usr/bin/env bash
# Build a local apt repository from the pistomp custom .deb packages in CACHE_DIR.
# The repo is written to REPO_DIR and can be used with a file:// apt source.
set -eu

ROOT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)"

# shellcheck source=config.sh
source "${ROOT_DIR}/config.sh"

CACHE_DIR="${CACHE_DIR:-${ROOT_DIR}/cache}"
REPO_DIR="${REPO_DIR:-${ROOT_DIR}/cache/apt-repo}"

echo "==> Building local apt repository in ${REPO_DIR}"

rm -rf "${REPO_DIR}"
mkdir -p "${REPO_DIR}/pool/main"
mkdir -p "${REPO_DIR}/dists/trixie/main/binary-arm64"

# Copy all pistomp .deb files into the pool (skip apt-cacher subdir, skip symlinks)
for deb in "${CACHE_DIR}"/*.deb; do
    [ -f "$deb" ] || continue
    cp "$deb" "${REPO_DIR}/pool/main/"
done

# Generate Packages.gz
(cd "${REPO_DIR}" && dpkg-scanpackages --arch arm64 pool/main /dev/null \
    > "dists/trixie/main/binary-arm64/Packages")
gzip -9 -c "${REPO_DIR}/dists/trixie/main/binary-arm64/Packages" \
    > "${REPO_DIR}/dists/trixie/main/binary-arm64/Packages.gz"

# Generate Release file
cat > "${REPO_DIR}/dists/trixie/Release" <<EOF
Origin: pistomp
Label: pistomp
Suite: trixie
Codename: trixie
Date: $(date -Ru)
Architectures: arm64
Components: main
Description: pi-Stomp custom packages
EOF

echo "==> Local apt repo ready at ${REPO_DIR}"
echo "    Packages: $(find "${REPO_DIR}/pool/main" -name '*.deb' | wc -l)"
