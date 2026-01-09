## Purpose

Builds the bootable OS image for pi-Stomp hardware.
Based on [pi-gen](https://github.com/RPI-Distro/pi-gen) (Debian/Raspberry Pi OS image builder).

## Ecosystem Context

Produces the foundation `pistompOS-lite.img.xz` flashed to SD cards.
Integrates components:
1.  **Base OS**: Raspberry Pi OS Lite (Debian Bookworm).
2.  **Kernel**: Realtime (RT) kernel (64-bit ARM).
3.  **Audio Engine**: JACK2, MOD-Host, MOD-UI (Stage 2).
4.  **Application**: `pi-stomp` python codebase, LV2 plugins, User Data (Stage 3).

## Architecture

Build process executes ordered stages.

| Stage | Description | Key Contents |
| :--- | :--- | :--- |
| **0-1** | Bootstrap | Base Debian system, bootloader. |
| **2** | System/Audio | RT Kernel, JACK, MOD services, System tweaks. |
| **3** | Application | `pi-stomp` repo, default pedalboards, plugins, wifi-hotspot. |

## Hardware Targets

-   **Architecture**: `arm64` (64-bit).
-   **Devices**: Raspberry Pi 3, 4, 5, Zero 2 W.
-   **Audio**: IQAudio DAC+ (configured in Stage 3 `alsa-base.conf`).

## Usage

### Prerequisites
-   Docker (recommended)
-   ~20GB Disk Space

### Build Image
Full build inside Docker container.

```bash
# Clean previous builds
rm -rf deploy/*

# Run build
./build-docker.sh
```

Result: `deploy/image_...pistompOS-lite.img.xz`

### Customization
-   **Config**: Edit `config` file (hostname, passwords, version).
-   **Packages**: Add/Remove in `stage*/00-packages`.
-   **Services**: Modify `stage2/05-pistomp/files/services/`.

## Development

### Fast Iteration (Live Device)
Do not rebuild image for component updates. Use `scripts/builder/INSPIRATION.sh` (acts as `reinstall.sh`) to update specific components on a running pi-Stomp.

```bash
# On the pi-stomp device
./INSPIRATION.sh mod-ui      # Reinstall/Update mod-ui
./INSPIRATION.sh mod-host    # Reinstall/Update mod-host
./INSPIRATION.sh all         # Rebuild all audio components
```

**Supported Components:**
-   `mod-ui` (MOD Web Interface)
-   `mod-host` (LV2 Host)
-   `jack2` (Audio Engine)
-   `hylia` (Ableton Link)
-   `lilv` (LV2 Library)
-   `browsepy` (File Manager)
-   `amidithru`, `mod-midi-merger`, `mod-ttymidi`, `touchosc2midi`

### System/Kernel Updates
Requires full image rebuild.

1.  **Kernel Packages**: Place new `.deb` files in `stage2/05-pistomp/files/sys/`.
2.  **Kernel Install**: Update `stage2/05-pistomp/03-run.sh` to:
    *   Install the new `.deb` packages.
    *   Update the manual file copy/move operations to `/boot/firmware/` for the new kernel version.
3.  **Rebuild**: Run `./build-docker.sh`.

### Workflow
1.  **Code Changes**: Modify `pi-stomp` python code -> Push to git.
2.  **Image Update**: Stage 3 clones latest `pistomp-v3` branch.
3.  **Rebuild**: Run `./build-docker.sh`.
