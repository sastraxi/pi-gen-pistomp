#!/bin/bash -e
#
# MOD Component Installation Script
# Based on pi-gen-pistomp initial image build instructions
#
# Usage:
#   ./reinstall.sh <component> [component2] [...] [options]
#
# Components:
#   hylia              Link library for Ableton Link
#   jack2              JACK Audio Connection Kit
#   browsepy           File browser web interface
#   mod-host           LV2 host for MOD
#   mod-ui             MOD UI web interface
#   amidithru          MIDI throughput utility
#   touchosc2midi      TouchOSC to MIDI bridge
#   mod-midi-merger    MIDI merger utility
#   mod-ttymidi        TTY MIDI interface
#   lilv               LV2 library
#   all                Install all components
#
# Options:
#   --no-restart       Don't restart services after installation
#   --help             Show this help message
#
# Environment Variables:
#   MOD_UI_PATH        Path to local mod-ui directory (instead of cloning from git)
#                      Example: MOD_UI_PATH=/Users/cam/dev/mod-ui ./reinstall.sh mod-ui
#

set -e

# Default options
RESTART_SERVICES=true
USER_NAME="${USER}"
TMP_DIR="/home/${USER_NAME}/tmp"
COMPONENTS=()

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-restart)
            RESTART_SERVICES=false
            shift
            ;;
        --help)
            grep '^#' "$0" | grep -v '#!/bin/bash' | sed 's/^# //'
            exit 0
            ;;
        hylia|jack2|browsepy|mod-host|mod-ui|amidithru|touchosc2midi|mod-midi-merger|mod-ttymidi|lilv|all)
            COMPONENTS+=("$1")
            shift
            ;;
        *)
            echo "Unknown component or option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if at least one component was specified
if [ ${#COMPONENTS[@]} -eq 0 ]; then
    echo "Error: No components specified"
    echo ""
    echo "Usage: $0 <component> [component2] [...] [options]"
    echo ""
    echo "Examples:"
    echo "  $0 mod-ui"
    echo "  $0 lilv mod-ui"
    echo "  $0 all"
    echo ""
    echo "Use --help for more information"
    exit 1
fi

# Expand 'all' to all components
if [[ " ${COMPONENTS[@]} " =~ " all " ]]; then
    COMPONENTS=(hylia jack2 browsepy mod-host mod-ui amidithru touchosc2midi mod-midi-merger mod-ttymidi lilv)
fi

echo "==========================================="
echo "MOD Component Installation Script"
echo "==========================================="
echo "Components to install: ${COMPONENTS[*]}"
echo "Restart services: $RESTART_SERVICES"
if [ -n "$MOD_UI_PATH" ]; then
    echo "Using local mod-ui: $MOD_UI_PATH"
fi
echo ""

# Create temporary directory
mkdir -p "${TMP_DIR}"
cd "${TMP_DIR}"

# Determine which services to stop/start based on components
STOP_JACK=false
STOP_MOD_HOST=false
STOP_MOD_UI=false

for component in "${COMPONENTS[@]}"; do
    case $component in
        jack2)
            STOP_JACK=true
            STOP_MOD_HOST=true
            STOP_MOD_UI=true
            ;;
        mod-host|lilv)
            STOP_MOD_HOST=true
            STOP_MOD_UI=true
            ;;
        mod-ui|hylia)
            STOP_MOD_UI=true
            ;;
    esac
done

# Stop services
echo "Stopping services..."
if [ "$STOP_MOD_UI" = true ]; then
    echo "  Stopping mod-ui..."
    sudo systemctl stop mod-ui.service || true
fi
if [ "$STOP_MOD_HOST" = true ]; then
    echo "  Stopping mod-host..."
    sudo systemctl stop mod-host.service || true
fi
if [ "$STOP_JACK" = true ]; then
    echo "  Stopping jack..."
    sudo systemctl stop jack.service || true
fi
echo ""

# Function to install Hylia
install_hylia() {
    echo "==========================================="
    echo "Installing Hylia..."
    echo "==========================================="
    cd "${TMP_DIR}"
    if [ -d "Hylia" ]; then
        rm -rf Hylia
    fi
    export NOOPT=true
    git clone --recursive https://github.com/falkTX/Hylia.git
    cd Hylia
    make
    sudo make install
    cd ..
    echo ""
}

# Function to install jack2
install_jack2() {
    echo "==========================================="
    echo "Installing jack2..."
    echo "==========================================="
    cd "${TMP_DIR}"
    if [ -d "jack2" ]; then
        rm -rf jack2
    fi
    git clone https://github.com/micahvdm/jack2.git
    cd jack2
    ./waf configure
    ./waf build
    sudo ./waf install
    cd ..
    echo ""
}

# Function to install browsepy
install_browsepy() {
    echo "==========================================="
    echo "Installing browsepy..."
    echo "==========================================="
    cd "${TMP_DIR}"
    if [ -d "browsepy" ]; then
        rm -rf browsepy
    fi
    git clone https://github.com/micahvdm/browsepy.git
    cd browsepy
    sudo pip3 install ./
    cd ..
    echo ""
}

# Function to install mod-host
install_mod_host() {
    echo "==========================================="
    echo "Installing mod-host..."
    echo "==========================================="
    cd "${TMP_DIR}"
    if [ -d "mod-host" ]; then
        rm -rf mod-host
    fi
    git clone https://github.com/micahvdm/mod-host.git
    cd mod-host
    make
    sudo make install
    cd ..
    echo ""
}

# Function to install mod-ui
install_mod_ui() {
    echo "==========================================="
    echo "Installing mod-ui..."
    echo "==========================================="

    # Remove old mod-ui installation
    echo "Removing old mod-ui installation..."
    sudo pip3 uninstall -y mod-ui || true

    # Determine source directory
    if [ -n "$MOD_UI_PATH" ]; then
        # Use local path
        if [ ! -d "$MOD_UI_PATH" ]; then
            echo "ERROR: MOD_UI_PATH is set but directory does not exist: $MOD_UI_PATH"
            exit 1
        fi
        echo "Using local mod-ui from: $MOD_UI_PATH"
        MOD_UI_SOURCE="$MOD_UI_PATH"
    else
        # Clone from git
        cd "${TMP_DIR}"
        if [ -d "mod-ui" ]; then
            rm -rf mod-ui
        fi
        echo "Cloning mod-ui from git..."
        git clone https://github.com/TreeFallSound/mod-ui.git
        MOD_UI_SOURCE="${TMP_DIR}/mod-ui"
    fi

    cd "$MOD_UI_SOURCE"
    chmod +x setup.py

    # Build utils
    echo "Building mod-ui utils..."
    cd utils
    make clean || true
    make
    cd ..

    # Install mod-ui
    echo "Installing mod-ui..."
    sudo ./setup.py install

    # Copy default pedalboard if it doesn't exist
    if [ ! -d "/home/${USER_NAME}/data/.pedalboards" ]; then
        echo "Creating default pedalboard..."
        mkdir -p /home/${USER_NAME}/data/.pedalboards
        if [ -d "default.pedalboard" ]; then
            cp -r default.pedalboard /home/${USER_NAME}/data/.pedalboards/
        fi
    fi

    # Fix tornado compatibility issue
    echo "Applying tornado compatibility fix..."
    TORNADO_PATH=$(python3 -c "import tornado, os; print(os.path.dirname(tornado.__file__))" 2>/dev/null || echo "")
    if [ -n "$TORNADO_PATH" ] && [ -f "$TORNADO_PATH/httputil.py" ]; then
        sudo sed -i -e 's/collections.MutableMapping/collections.abc.MutableMapping/g' "$TORNADO_PATH/httputil.py" || true
    fi

    cd "${TMP_DIR}"
    echo ""
}

# Function to install amidithru
install_amidithru() {
    echo "==========================================="
    echo "Installing amidithru..."
    echo "==========================================="
    cd "${TMP_DIR}"
    if [ -d "amidithru" ]; then
        rm -rf amidithru
    fi
    git clone https://github.com/BlokasLabs/amidithru.git
    cd amidithru
    sed -i 's/CXX=g++.*/CXX=g++/' Makefile
    sudo make install
    cd ..
    echo ""
}

# Function to install touchosc2midi
install_touchosc2midi() {
    echo "==========================================="
    echo "Installing touchosc2midi..."
    echo "==========================================="
    cd "${TMP_DIR}"
    if [ -d "touchosc2midi" ]; then
        rm -rf touchosc2midi
    fi
    git clone https://github.com/micahvdm/touchosc2midi.git
    cd touchosc2midi
    sudo pip3 install ./
    cd ..
    echo ""
}

# Function to install mod-midi-merger
install_mod_midi_merger() {
    echo "==========================================="
    echo "Installing mod-midi-merger..."
    echo "==========================================="
    cd "${TMP_DIR}"
    if [ -d "mod-midi-merger" ]; then
        rm -rf mod-midi-merger
    fi
    git clone https://github.com/micahvdm/mod-midi-merger.git
    cd mod-midi-merger
    mkdir -p build && cd build
    cmake ..
    make
    sudo make install
    cd ../..
    echo ""
}

# Function to install mod-ttymidi
install_mod_ttymidi() {
    echo "==========================================="
    echo "Installing mod-ttymidi..."
    echo "==========================================="
    cd "${TMP_DIR}"
    if [ -d "mod-ttymidi" ]; then
        rm -rf mod-ttymidi
    fi
    git clone https://github.com/moddevices/mod-ttymidi.git
    cd mod-ttymidi
    sudo make install
    cd ..
    echo ""
}

# Function to install lilv
install_lilv() {
    echo "==========================================="
    echo "Installing lilv..."
    echo "==========================================="
    cd "${TMP_DIR}"
    if [ ! -f "lilv-0.24.12.tar.bz2" ]; then
        wget http://download.drobilla.net/lilv-0.24.12.tar.bz2
    fi
    if [ -d "lilv-0.24.12" ]; then
        rm -rf lilv-0.24.12
    fi
    tar xvf lilv-0.24.12.tar.bz2
    cd lilv-0.24.12

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    # Add -fPIC flag for static library to be linkable into shared libraries
    export CFLAGS="${CFLAGS} -fPIC"
    export CXXFLAGS="${CXXFLAGS} -fPIC"
    ./waf configure --prefix=/usr/local --static --static-progs --no-shared --no-utils --no-bash-completion --pythondir=/usr/local/lib/python${PYTHON_VERSION}/dist-packages
    ./waf build
    sudo ./waf install
    cd ..
    echo ""
}

# Install components in order
for component in "${COMPONENTS[@]}"; do
    case $component in
        hylia)
            install_hylia
            ;;
        jack2)
            install_jack2
            ;;
        browsepy)
            install_browsepy
            ;;
        mod-host)
            install_mod_host
            ;;
        mod-ui)
            install_mod_ui
            ;;
        amidithru)
            install_amidithru
            ;;
        touchosc2midi)
            install_touchosc2midi
            ;;
        mod-midi-merger)
            install_mod_midi_merger
            ;;
        mod-ttymidi)
            install_mod_ttymidi
            ;;
        lilv)
            install_lilv
            ;;
    esac
done

# Clean up
echo "Cleaning up temporary files..."
cd ~
rm -rf "${TMP_DIR}"

# Restart services
if [ "$RESTART_SERVICES" = true ]; then
    echo ""
    echo "Restarting services..."

    if [ "$STOP_JACK" = true ]; then
        echo "  Starting jack..."
        sudo systemctl start jack.service || true
        sleep 2
    fi

    if [ "$STOP_MOD_HOST" = true ]; then
        echo "  Starting mod-host..."
        sudo systemctl start mod-host.service || true
        sleep 1
    fi

    if [ "$STOP_MOD_UI" = true ]; then
        echo "  Starting mod-ui..."
        sudo systemctl start mod-ui.service || true
    fi

    echo ""
    echo "Service status:"
    if [ "$STOP_JACK" = true ]; then
        sudo systemctl status jack.service --no-pager || true
    fi
    if [ "$STOP_MOD_HOST" = true ]; then
        sudo systemctl status mod-host.service --no-pager || true
    fi
    if [ "$STOP_MOD_UI" = true ]; then
        sudo systemctl status mod-ui.service --no-pager || true
    fi
fi

echo ""
echo "==========================================="
echo "Installation complete!"
echo "==========================================="
echo ""
if [ -n "$MOD_UI_PATH" ]; then
    echo "Installed mod-ui from local path: $MOD_UI_PATH"
    echo ""
fi
echo "Installed components: ${COMPONENTS[*]}"
echo ""
echo "You can check the logs with:"
echo "  sudo journalctl -u mod-ui.service -f"
echo ""
echo "mod-ui should be accessible at:"
echo "  http://localhost (or your device's IP address)"
echo ""
