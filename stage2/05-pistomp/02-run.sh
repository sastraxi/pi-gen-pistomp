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
echo "Installing Hylia via pistomp-builder..."
./deploy.sh falkTX/Hylia

echo "----------------------------------------------------------------"
echo "Installing jack2 via pistomp-builder..."
./deploy.sh micahvdm/jack2

echo "----------------------------------------------------------------"
echo "Installing browsepy via pistomp-builder..."
./deploy.sh micahvdm/browsepy

echo "----------------------------------------------------------------"
echo "Installing mod-host via pistomp-builder..."
./deploy.sh micahvdm/mod-host

echo "----------------------------------------------------------------"
echo "Installing mod-ui via pistomp-builder..."
./deploy.sh TreeFallSound/mod-ui

echo "----------------------------------------------------------------"
echo "Installing amidithru via pistomp-builder..."
./deploy.sh BlokasLabs/amidithru

echo "----------------------------------------------------------------"
echo "Installing touchosc2midi via pistomp-builder..."
./deploy.sh micahvdm/touchosc2midi

echo "----------------------------------------------------------------"
echo "Installing mod-midi-merger via pistomp-builder..."
./deploy.sh micahvdm/mod-midi-merger

echo "----------------------------------------------------------------"
echo "Installing mod-ttymidi via pistomp-builder..."
./deploy.sh moddevices/mod-ttymidi

echo "----------------------------------------------------------------"
echo "Installing lilv via pistomp-builder..."
./deploy.sh http://download.drobilla.net/lilv-0.24.12.tar.bz2

EOF