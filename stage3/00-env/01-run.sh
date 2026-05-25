#!/bin/bash -e

echo "Installing uv"

on_chroot << EOF
curl -LsSf https://astral.sh/uv/install.sh | sh
mv /root/.local/bin/uv /usr/local/bin/uv
mv /root/.local/bin/uvx /usr/local/bin/uvx
EOF
