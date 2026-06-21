# UX Parity with pistomp-arch

This document describes the work required to bring pi-gen-pistomp's runtime UX up to the standard set by pistomp-arch, independent of the packaging work in `PACKAGING.md` and the trixie upgrade in `UPGRADE-TRIXIE.md`. These are largely self-contained changes that can land on bookworm or trixie.

The reference implementation for all of this is in `../pistomp-arch/`. Read it before writing any of the equivalent code here.

---

## 1. LCD boot splash

**Current state:** Blank screen from power-on until pi-stomp fully initializes. During both firstboot reboots and normal boot, the user has no feedback that the device is alive.

**Target:** Logo visible within a few seconds of power-on; service startup narrates progress; shutdown/reboot show a message before the screen goes dark.

### Implementation

**a. `lcd-splash` binary**

pistomp-arch ships a small C program (`/usr/bin/lcd-splash`) that writes a pre-rendered `.rgb565` file to the ILI9341 SPI display and optionally overlays a status line. Copy or adapt this from `../pistomp-arch/pkgbuilds/lcd-splash/` (or whatever package builds it). Install to `/usr/bin/lcd-splash` and place the splash image at `/usr/share/pistomp/splash.rgb565`.

If there is no existing package, this is a small C program (~100 lines) that opens `/dev/spidev0.0`, sends the SPI init sequence for ILI9341, and writes the framebuffer. pistomp-arch has a working implementation.

**b. `pistomp-lcd-splash.service`**

```ini
[Unit]
Description=pi-Stomp LCD boot splash
DefaultDependencies=no
After=local-fs.target

[Service]
Type=oneshot
ExecStart=/usr/bin/lcd-splash /usr/share/pistomp/splash.rgb565 "Booting..."
RemainAfterExit=yes

[Install]
WantedBy=sysinit.target
```

Enable via symlink in `/etc/systemd/system/sysinit.target.wants/`. This runs before networking, before jack, before anything — the LCD gets the logo within ~3 seconds of power-on.

**c. Service startup narration**

Add `ExecStartPre=/usr/bin/lcd-splash /usr/share/pistomp/splash.rgb565 "<message>"` to key services:

```ini
# jack.service
ExecStartPre=-/usr/bin/lcd-splash /usr/share/pistomp/splash.rgb565 "Starting audio..."

# mod-host.service
ExecStartPre=-/usr/bin/lcd-splash /usr/share/pistomp/splash.rgb565 "Starting mod-host..."

# mod-ui.service
ExecStartPre=-/usr/bin/lcd-splash /usr/share/pistomp/splash.rgb565 "Starting web interface..."
```

The `-` prefix means failure is non-fatal (if lcd-splash isn't installed yet, the service still starts).

**d. Shutdown and reboot splash**

```ini
# lcd-reboot.service — install in reboot.target.wants
[Unit]
Description=Show reboot message on LCD
DefaultDependencies=no
Before=reboot.target
After=final.target

[Service]
Type=oneshot
ExecStart=/usr/bin/lcd-splash /usr/share/pistomp/splash.rgb565 "Rebooting..."

[Install]
WantedBy=reboot.target
```

```ini
# lcd-shutdown.service — install in poweroff.target.wants
[Unit]
Description=Show shutdown message on LCD
DefaultDependencies=no
Before=poweroff.target

[Service]
Type=oneshot
ExecStart=/usr/bin/lcd-splash /usr/share/pistomp/splash.rgb565 "Shutting down..."

[Install]
WantedBy=poweroff.target
```

For the "Safe to power off" message at the very end (after filesystems unmount), pistomp-arch uses a `system-shutdown/` drop-in. Copy `../pistomp-arch/files/lcd-safe-poweroff.sh` to `/usr/lib/systemd/system-shutdown/lcd-safe-poweroff.sh`.

**Where to add this in pi-gen:** Add the service unit files to `stage2/05-pistomp/files/services/` and install + enable them in `01-run.sh`.

---

## 2. Service readiness probes (fixing the restart-loop boot time)

**Current state:** `mod-ui.service` declares `After=mod-host.service` but mod-host doesn't emit a readiness signal — it's `Type=simple`, so systemd considers it "started" the moment the process exists, not when it's actually listening on its port. mod-ui starts immediately, finds mod-host not ready, and crashes. systemd restarts it. This loop adds minutes to boot time.

**Target:** mod-ui waits until mod-host is actually accepting connections before it starts.

### Implementation

**a. `wait-for-mod-host.sh`**

```bash
#!/bin/bash
# Wait for mod-host to be listening on TCP port 5555
timeout=30
while ! nc -z localhost 5555 2>/dev/null; do
    sleep 0.5
    timeout=$((timeout - 1))
    [ $timeout -le 0 ] && { echo "mod-host did not start in time"; exit 1; }
done
```

Install to `/usr/local/bin/wait-for-mod-host.sh`, mode 755.

**b. Wire into `mod-ui.service`**

```ini
[Service]
ExecStartPre=/usr/local/bin/wait-for-mod-host.sh
ExecStart=/usr/bin/authbind /usr/local/bin/mod-ui
```

**Where to add this:** Install the script in `stage2/05-pistomp/01-run.sh`; update `stage2/05-pistomp/files/services/mod-ui.service`.

---

## 3. `MOD_HTML_DIR` fix (mod-ui crashes on startup)

**Current state:** `mod-ui.service` sets `MOD_HTML_DIR=/usr/local/share/mod/html`. When mod-ui is installed with `pip install -e` (editable), `data_files` in `setup.py` are never copied, so this path doesn't exist. mod-ui crashes immediately on every boot until this path is created.

**Fix:** Point `MOD_HTML_DIR` at the source tree where the editable install lives:

```ini
Environment=MOD_HTML_DIR=/home/pistomp/tmp/mod-ui/html
Environment=MOD_DEFAULT_PEDALBOARD=/home/pistomp/tmp/mod-ui/default.pedalboard
```

The exact path depends on where `02-run.sh` clones mod-ui. In the current script it's `/home/${FIRST_USER_NAME}/tmp/mod-ui`. Adjust accordingly, and make sure that directory isn't cleaned up by `04-run.sh` (which currently does `rm -rf /home/${FIRST_USER_NAME}/tmp`).

**Where to add this:** Update `stage2/05-pistomp/files/services/mod-ui.service`. Remove mod-ui from the `tmp/` cleanup in `04-run.sh`.

---

## 4. `pistomp.conf` firstboot paradigm

**Current state:** User configuration (WiFi, hostname, password) is handled by the RPi Imager 1.x pre-flash mechanism, which injects `userconf` and modifies `cmdline.txt`. This doesn't work reliably with modern RPi Imager 2.x, and requires the user to configure through the Imager rather than editing a plain text file.

**Target:** A `pistomp.conf` file on the FAT32 boot partition (editable in any text editor on any OS after flashing) that firstboot reads and applies, just like pistomp-arch.

### Implementation

**a. `pistomp.conf` template**

```bash
# pistomp.conf — User configuration
# Edit this file on the boot partition after flashing.
# Settings are applied on first boot, then this file is left in place.
# To re-apply, delete /boot/firmware/firstboot.done and reboot.

WIFI_SSID=""
WIFI_PASSWORD=""
WIFI_COUNTRY="US"
HOSTNAME="pistomp"
USER_PASSWORD="pistomp"
TIMEZONE="US/Central"
SSH_AUTHORIZED_KEY=""
JACK_SAMPLE_RATE="48000"
JACK_PERIOD="64"
```

Install to `${ROOTFS_DIR}/boot/firmware/pistomp.conf` from `stage2/05-pistomp/files/pistomp.conf`.

**b. Rewrite `firstboot.sh`** to source `pistomp.conf`:

```bash
#!/bin/bash
set -e
CONF="/boot/firmware/pistomp.conf"

[ -f "${CONF}" ] && source "${CONF}"

# WiFi
if [ -n "${WIFI_SSID:-}" ]; then
    printf 'options cfg80211 ieee80211_regdom=%s\n' "${WIFI_COUNTRY:-US}" \
        > /etc/modprobe.d/cfg80211.conf
    nmcli connection delete "preconfigured" 2>/dev/null || true
    nmcli connection add type wifi ifname wlan0 con-name "preconfigured" \
        ssid "${WIFI_SSID}" \
        wifi-sec.key-mgmt wpa-psk wifi-sec.psk "${WIFI_PASSWORD}" \
        connection.autoconnect yes
fi

# Hostname
if [ -n "${HOSTNAME:-}" ] && [ "${HOSTNAME}" != "pistomp" ]; then
    hostnamectl set-hostname "${HOSTNAME}"
    sed -i "s/pistomp/${HOSTNAME}/g" /etc/hosts
fi

# Password
[ -n "${USER_PASSWORD:-}" ] && echo "pistomp:${USER_PASSWORD}" | chpasswd

# Timezone
[ -n "${TIMEZONE:-}" ] && ln -sf "/usr/share/zoneinfo/${TIMEZONE}" /etc/localtime

# SSH key
if [ -n "${SSH_AUTHORIZED_KEY:-}" ]; then
    mkdir -p /home/pistomp/.ssh
    echo "${SSH_AUTHORIZED_KEY}" >> /home/pistomp/.ssh/authorized_keys
    chmod 700 /home/pistomp/.ssh
    chmod 600 /home/pistomp/.ssh/authorized_keys
    chown -R pistomp:pistomp /home/pistomp/.ssh
fi

# JACK settings (written to /etc/default/jack, read by jack.service)
cat > /etc/default/jack <<EOF
JACK_SAMPLE_RATE="${JACK_SAMPLE_RATE:-48000}"
JACK_PERIOD="${JACK_PERIOD:-64}"
EOF

# ... existing: RT kernel switch, ALSA state, Pi model detection, pi5 EEPROM ...

touch /boot/firmware/firstboot.done
systemctl disable firstboot.service
reboot
```

**c. Disable RPi Imager customization injection**

Set `DISABLE_FIRST_BOOT_USER_RENAME=1` (already done) and additionally remove or ignore the `userconf.txt` mechanism. Since we're creating the `pistomp` user in the pi-gen build itself (not via Imager), the Imager's user creation is irrelevant.

**Where to add this:** Replace `stage2/05-pistomp/files/firstboot.sh` with the rewritten version. Add `pistomp.conf` to `stage2/05-pistomp/files/`. Update `04-run.sh` to install `pistomp.conf` to `${ROOTFS_DIR}/boot/firmware/`.

---

## 5. RT kernel baked in at image build time (eliminating the extra reboot)

**Current state:** `firstboot.sh` copies `config_pistomp.txt` → `config.txt` on first boot to activate the RT kernel overlay. This means the device boots the stock RPi kernel on first power-on, then reboots into RT. Two kernel boots before the device is usable.

**Target:** Bake the RT kernel config into `config.txt` at image build time so the device boots RT on first power-on, no extra reboot.

### Implementation

In `stage2/05-pistomp/03-run.sh`, after installing the RT kernel `.deb` files, apply the RT config at build time rather than at firstboot:

```bash
# Instead of placing config_pistomp.txt on the boot partition for firstboot to swap:
install -m 644 files/config_pistomp.txt ${ROOTFS_DIR}/boot/firmware/config.txt
```

Remove the `config.txt` swap step from `firstboot.sh`. The remaining firstboot tasks (WiFi, hostname, ALSA state, pi model detection, pi5 EEPROM) do not require a separate "switch to RT kernel" reboot — they can all happen on the same first boot with the RT kernel already active.

**Caveat:** Test that the RT kernel boots correctly with the stock RPi OS initramfs on first flash, before firstboot has run. On bookworm this should be fine since the RT kernel `.deb` installs its initramfs correctly at build time. On trixie, rebuild the RT kernel `.deb` files first (see `UPGRADE-TRIXIE.md` §3.4).

---

## 6. Filesystem expansion without the SysV init script

**Current state:** `resize2fs_once` is a SysV init script that runs at runlevel 3 on first boot, expands the root partition, then removes itself. SysV init is a relic; it also doesn't show progress on the LCD.

**Target:** A systemd-native `growpart`/`resize2fs` call inside firstboot, with LCD narration.

### Implementation

Remove `stage2/01-sys-tweaks/files/resize2fs_once` and its install in `01-run.sh`. Add to `firstboot.sh`:

```bash
/usr/bin/lcd-splash /usr/share/pistomp/splash.rgb565 "Expanding filesystem..."
ROOT_DEV="$(findmnt -n -o SOURCE /)"
DISK="/dev/$(lsblk -no PKNAME "${ROOT_DEV}")"
PARTNUM="$(echo "${ROOT_DEV}" | grep -o '[0-9]*$')"
growpart "${DISK}" "${PARTNUM}" || true
resize2fs "${ROOT_DEV}" || true
```

`growpart` is provided by `cloud-guest-utils` (already available on RPi OS). This runs under systemd so it gets logged, and the LCD message replaces the silent SysV script.

---

## 7. Passwordless sudo hardening (trixie)

**Current state:** RPi OS bookworm enables passwordless sudo for the first user. The trixie base (as of the 2026-04-13 release) disables this. Several places in the build scripts and `firstboot.sh` use bare `sudo` commands that will hang if passwordless sudo is gone.

**Audit checklist for `firstboot.sh`:**

- All `sudo` calls should be removed — `firstboot.service` runs as root, so `sudo` is never needed
- `rc.local` additions that use `sudo iw dev wlan0 set power_save off` — `rc.local` already runs as root, drop the `sudo`

This is a trixie-only concern but worth fixing now since the pattern (`sudo` inside a root script) is just noise.

---

## Suggested implementation order

These can be done independently; order by impact:

1. **`MOD_HTML_DIR` fix** — eliminates the restart loop; biggest boot time win with least code
2. **Readiness probe (`wait-for-mod-host.sh`)** — second-biggest boot time win
3. **`pistomp.conf` firstboot** — user experience improvement, largely a rewrite of `firstboot.sh`
4. **RT kernel baked in** — eliminates one boot; requires testing with RT kernel + trixie
5. **LCD splash** — requires the `lcd-splash` binary to exist; port from pistomp-arch
6. **`resize2fs_once` → systemd** — cleanup; minor boot time improvement

Items 1–3 can land without the trixie upgrade. Items 4–6 are independent but benefit from testing together.
