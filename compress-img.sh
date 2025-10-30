#!/usr/bin/env bash
set -euo pipefail

# Source glob
SRC_GLOB="work/pistompOS/export-image/*pistompOS-lite.img"

# Check that a source file exists
SRC_FILE=$(ls $SRC_GLOB 2>/dev/null | head -n 1 || true)
if [[ -z "$SRC_FILE" ]]; then
    echo "ERROR: Source file not found at $SRC_GLOB"
    exit 1
fi

# Destination filename
DATE=$(date +"%Y-%m-%d")
DEST="pistompOS-${DATE}.img.xz"

# If dest already exists, back it up (pistompOS-YYYY-MM-DD.img.xz.bak, .bak1, etc.)
if [[ -f "$DEST" ]]; then
    i=0
    while true; do
        BACKUP="${DEST}.bak${i}"
        if [[ ! -f "$BACKUP" ]]; then
            echo "Backing up existing $DEST to $BACKUP"
            mv "$DEST" "$BACKUP"
            break
        fi
        ((i++))
    done
fi

# Run compression
echo "Compressing $SRC_FILE → $DEST ..."
xz -7e -T0 --memlimit-compress=2GiB --lzma2=dict=48MiB,nice=192,depth=64 -v -c "$SRC_FILE" > "$DEST"

echo "Done: $DEST"

