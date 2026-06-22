#!/bin/bash -e

echo "Installing MOD software"
on_chroot << EOF

mkdir -p /home/${FIRST_USER_NAME}/tmp
cd /home/${FIRST_USER_NAME}/tmp

# uv: Python version manager (installs Python 3.11 for mod-ui) + also used in stage3
pip3 install uv

# Python 3.11 goes to /opt/mod-ui-python so the venv symlink is valid on the Pi
UV_PYTHON_INSTALL_DIR=/opt/mod-ui-python uv python install 3.11

# Install custom .deb packages (built by debpkgs/*/build.sh, served from
# the pistomp apt repo or cached locally during image build).
apt-get install -y \
    hylia \
    jack2-pistomp \
    amidithru \
    mod-host-pistomp \
    mod-midi-merger \
    mod-ttymidi \
    sfizz-pistomp \
    fluidsynth-headless \
    lcd-splash \
    jack-capture

# python3-lilv and liblilv-dev are available via apt on trixie (>=0.24.26).
# No source build needed — installed via 00-packages.

[ ! -d browsepy ] && git clone https://github.com/micahvdm/browsepy.git
cd browsepy
pip3 install ./
cd ..

# mod-ui requires tornado==4.3 which is incompatible with Python 3.13.
# Run it in an isolated Python 3.11 venv, the same pattern as pistomp-arch.
[ ! -d mod-ui ] && git clone https://github.com/TreeFallSound/mod-ui.git
cd mod-ui
chmod +x setup.py
cd utils
make
cd ..
UV_PYTHON_INSTALL_DIR=/opt/mod-ui-python uv venv --python 3.11 /opt/mod-ui-venv
/opt/mod-ui-venv/bin/pip install tornado==4.3
# tornado 4.x uses collections.MutableMapping, removed in Python 3.10+.
sed -i -e 's/collections\.MutableMapping/collections.abc.MutableMapping/g' \
    /opt/mod-ui-venv/lib/python3.11/site-packages/tornado/httputil.py
/opt/mod-ui-venv/bin/python setup.py install
cp -r default.pedalboard /home/${FIRST_USER_NAME}/data/.pedalboards
cd ..

[ ! -d touchosc2midi ] && git clone https://github.com/BlokasLabs/touchosc2midi.git
cd touchosc2midi
pip3 install ./
cd ..

EOF
