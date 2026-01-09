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

# Pre-process arguments to allow --ssh to default to pistomp@pistomp.local
processed_args=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --ssh)
            if [[ -z "$2" || "$2" == -* ]]; then
                processed_args+=("--ssh" "pistomp@pistomp.local")
            else
                processed_args+=("--ssh" "$2")
                shift
            fi
            ;;
        *)
            processed_args+=("$1")
            ;;
    esac
    shift
done

# Execute
# We point uv to the project directory
PYTHONPATH="$SCRIPT_DIR" uv run --project "$SCRIPT_DIR" python3 -m pistomp_builder.main "${processed_args[@]}"
