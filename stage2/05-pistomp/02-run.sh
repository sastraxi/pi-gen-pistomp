#!/bin/bash -e

echo "Installing MOD software via pistomp-builder"

# Copy builder tool to image
mkdir -p "${ROOTFS_DIR}/opt/pistomp-builder"
cp -r "${BASE_DIR}/builder/"* "${ROOTFS_DIR}/opt/pistomp-builder/"

on_chroot << EOF

cd /opt/pistomp-builder

export FIRST_USER_NAME="${FIRST_USER_NAME}"

# Install components
chmod +x deploy.sh

echo "----------------------------------------------------------------"
echo "Installing Hylia..."
./deploy.sh deploy falkTX/Hylia

echo "----------------------------------------------------------------"
echo "Installing jack2..."
./deploy.sh deploy jackaudio/jack2#v1.9.22

echo "----------------------------------------------------------------"
echo "Installing lilv (Python bindings only)..."
./deploy.sh deploy lilv

echo "----------------------------------------------------------------"
echo "Installing browsepy..."
./deploy.sh deploy micahvdm/browsepy

echo "----------------------------------------------------------------"
echo "Installing mod-host..."
./deploy.sh deploy micahvdm/mod-host

echo "----------------------------------------------------------------"
echo "Installing mod-ui..."
./deploy.sh deploy sastraxi/mod-ui#fix/effect-parameter-from-snapshot

echo "----------------------------------------------------------------"
echo "Installing amidithru..."
./deploy.sh deploy BlokasLabs/amidithru

echo "----------------------------------------------------------------"
echo "Installing touchosc2midi..."
./deploy.sh deploy micahvdm/touchosc2midi

echo "----------------------------------------------------------------"
echo "Installing mod-midi-merger..."
./deploy.sh deploy micahvdm/mod-midi-merger

echo "----------------------------------------------------------------"
echo "Installing mod-ttymidi..."
./deploy.sh deploy moddevices/mod-ttymidi

EOF
