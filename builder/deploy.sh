#!/bin/bash
set -e

# Resolve the directory where this script resides
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the python app using uv
# We assume 'uv' is in the PATH.
if ! command -v uv &> /dev/null; then
    echo "Error: 'uv' is not installed. Please install it."
    exit 1
fi

# Execute
# We point uv to the project directory
uv run --project "$SCRIPT_DIR" pistomp-builder "$@"
