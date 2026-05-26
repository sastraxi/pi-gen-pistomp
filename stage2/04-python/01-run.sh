#!/bin/bash -e

echo "Installing Python PIP packages"
on_chroot << EOF

rm -rf /usr/lib/python3.11/EXTERNALLY-MANAGED

pip3 install pyserial==3.0 pystache==0.5.4 aggdraw==1.3.11 scandir backports.shutil-get-terminal-size
pip3 install pycryptodomex
pip3 install tornado==4.3
pip3 install Pillow==9.4.0
pip3 install cython
pip3 install python-config
pip3 install JACK-Client
pip3 install flask
pip3 install unicategories
pip3 install scandir
pip3 install pep8
pip3 install flake8
pip3 install coverage
pip3 install pyaml
pip3 install sphinx
pip3 install netifaces==0.10.5
pip3 install mido==1.1.24
pip3 install docopt==0.6.2

EOF
echo "Done installing PIP packages"

# Extra hack for pi5
# TODO: this may not be needed anymore if pi-stomp was the only consumer;
# this is now handled by uv via pyproject.toml's dependency override
on_chroot << EOF
sudo apt-get -y remove python3-rpi.gpio
sudo apt-get -y install python3-rpi-lgpio
sudo apt install python3-rpi-lgpio
EOF
