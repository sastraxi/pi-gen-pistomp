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
echo "----------------------------------------------------------------"
echo "Installing Hylia via pistomp-builder..."
uv run --project . pistomp-builder deploy falkTX/Hylia

echo "----------------------------------------------------------------"
echo "Installing jack2 via pistomp-builder..."
uv run --project . pistomp-builder deploy micahvdm/jack2

echo "----------------------------------------------------------------"
echo "Installing browsepy via pistomp-builder..."
uv run --project . pistomp-builder deploy micahvdm/browsepy

echo "----------------------------------------------------------------"
echo "Installing mod-host via pistomp-builder..."
uv run --project . pistomp-builder deploy micahvdm/mod-host

echo "----------------------------------------------------------------"
echo "Installing mod-ui via pistomp-builder..."
uv run --project . pistomp-builder deploy TreeFallSound/mod-ui

echo "----------------------------------------------------------------"
echo "Installing amidithru via pistomp-builder..."
uv run --project . pistomp-builder deploy BlokasLabs/amidithru

echo "----------------------------------------------------------------"
echo "Installing touchosc2midi via pistomp-builder..."
uv run --project . pistomp-builder deploy micahvdm/touchosc2midi

echo "----------------------------------------------------------------"
echo "Installing mod-midi-merger via pistomp-builder..."
uv run --project . pistomp-builder deploy micahvdm/mod-midi-merger

echo "----------------------------------------------------------------"
echo "Installing mod-ttymidi via pistomp-builder..."
uv run --project . pistomp-builder deploy moddevices/mod-ttymidi

echo "----------------------------------------------------------------"
echo "Installing lilv via pistomp-builder..."
uv run --project . pistomp-builder deploy http://download.drobilla.net/lilv-0.24.12.tar.bz2

EOF