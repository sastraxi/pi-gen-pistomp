#!/bin/bash -e

echo "Installing MOD software via pistomp-builder"

# Copy builder tool to image
mkdir -p "${ROOTFS_DIR}/opt/pistomp-builder"
cp -r "${BASE_DIR}/builder/"* "${ROOTFS_DIR}/opt/pistomp-builder/"

on_chroot << EOF

cd /opt/pistomp-builder

# Install dependencies (sh, typer) using uv
# We rely on uv run to handle this.

export FIRST_USER_NAME="${FIRST_USER_NAME}"

# Install components
chmod +x deploy.sh

echo "----------------------------------------------------------------"
echo "Installing Hylia..."
./deploy.sh falkTX/Hylia

echo "----------------------------------------------------------------"
echo "Installing jack2..."
./deploy.sh micahvdm/jack2

echo "----------------------------------------------------------------"
echo "Installing browsepy..."
./deploy.sh micahvdm/browsepy

echo "----------------------------------------------------------------"
echo "Installing mod-host..."
./deploy.sh micahvdm/mod-host

echo "----------------------------------------------------------------"
echo "Installing mod-ui..."
./deploy.sh TreeFallSound/mod-ui

echo "----------------------------------------------------------------"
echo "Installing amidithru..."
./deploy.sh BlokasLabs/amidithru

echo "----------------------------------------------------------------"
echo "Installing touchosc2midi..."
./deploy.sh micahvdm/touchosc2midi

echo "----------------------------------------------------------------"
echo "Installing mod-midi-merger..."
./deploy.sh micahvdm/mod-midi-merger

echo "----------------------------------------------------------------"
echo "Installing mod-ttymidi..."
./deploy.sh moddevices/mod-ttymidi

echo "----------------------------------------------------------------"
echo "Installing lilv..."
./deploy.sh http://download.drobilla.net/lilv-0.24.12.tar.bz2

EOF
