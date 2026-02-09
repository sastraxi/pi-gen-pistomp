#!/bin/bash

echo "pi-Stomp files"

# ssh logo splash
install -m 666 files/display-pistomp-logo ${ROOTFS_DIR}/etc/update-motd.d/
chmod +x ${ROOTFS_DIR}/etc/update-motd.d/display-pistomp-logo

# banks default
install -m 644 files/banks.json ${ROOTFS_DIR}/home/${FIRST_USER_NAME}/data/

# Insure IQAudio card is pegged to hw:0 for jack
install -m 644 files/alsa-base.conf ${ROOTFS_DIR}/etc/modprobe.d

on_chroot << EOF

# Install pi-stomp via builder
echo "Installing pi-stomp via pistomp-builder..."
export FIRST_USER_NAME="${FIRST_USER_NAME}"
/opt/pistomp-builder/deploy.sh sastraxi/pi-stomp#fix/dialog-timeout

# pi-Stomp user-files
# Note: user-files are not yet a component in builder, keeping manual clone
echo "Cloning pi-stomp-user-files..."
git clone --recurse-submodules https://github.com/TreeFallSound/pi-stomp-user-files.git /home/${FIRST_USER_NAME}/data/user-files
chown -R ${FIRST_USER_NAME}:${FIRST_USER_NAME} /home/${FIRST_USER_NAME}/data/user-files

# Install pedalboards via builder
echo "Installing pi-stomp-pedalboards via pistomp-builder..."
/opt/pistomp-builder/deploy.sh sastraxi/dot-pedalboards

# Plugins
mkdir -p /home/${FIRST_USER_NAME}/tmp
pushd /home/${FIRST_USER_NAME}/tmp
wget https://www.treefallsound.com/downloads/lv2plugins.tar.gz
tar -zxf lv2plugins.tar.gz -C /home/${FIRST_USER_NAME}/
ln -s /home/${FIRST_USER_NAME}/.lv2 /home/${FIRST_USER_NAME}/data/.lv2
popd
rm -rf /home/${FIRST_USER_NAME}/tmp

EOF

# rc.local
bash -c "sed -i 's/exit 0//' ${ROOTFS_DIR}/etc/rc.local"
cat >> ${ROOTFS_DIR}/etc/rc.local <<EOF
logger --priority info --tag rc.local "rc.local start..."
sudo iw dev wlan0 set power_save off
(sleep 10;/usr/lib/pistomp-wifi/wifi_check.sh) &
logger --priority info --tag rc.local "rc.local completed successfully"
exit 0
EOF

# Version info
software_version=$(sudo git --work-tree ${ROOTFS_DIR}/home/pistomp/pi-stomp --git-dir ${ROOTFS_DIR}/home/pistomp/pi-stomp/.git describe --dirty="*" --always)
build_tag=$(git --work-tree $BASE_DIR --git-dir $BASE_DIR/.git describe --dirty="*" --always)
build_date=$(date +"%y%m%d")
printf '{"build-tag": "%s", "build-date": "%s", "software-version": "%s"}' $build_tag $build_date $software_version > ${ROOTFS_DIR}/home/pistomp/.osbuild

