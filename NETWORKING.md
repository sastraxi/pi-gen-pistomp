# Networking: pistomp-arch vs pi-gen-pistomp

This document maps every networking difference between the two image builders and states exactly what needs to change in pi-gen-pistomp. **pistomp-arch is the gold standard** — it is tested and working.

---

## 1. Stack comparison

| Component | pistomp-arch | pi-gen-pistomp | Match? |
|---|---|---|---|
| **Network manager** | NetworkManager (pacman) | NetworkManager (apt) | Yes |
| **NM plugins** | `keyfile` only | `ifupdown,keyfile` | No — pi-gen keeps deprecated `ifupdown` plugin |
| **NM dns** | `dns=dnsmasq` (in NM.conf directly) | `dns=dnsmasq` (patched in via diff) | Functional match, but pi-gen's patch approach is fragile |
| **Interface naming** | Predictable names disabled by udev rule: WiFi renamed to `wlan0`, ethernet is `end0` | Predictable names disabled system-wide via `raspi-config do_net_names 1`; WiFi stays `wlan0`, ethernet stays `eth0` | WiFi: match. Ethernet: different name (`end0` vs `eth0`) — affects NM connection profile |
| **Wired NM connection profile** | `/etc/NetworkManager/system-connections/wired-end0.nmconnection`: DHCP + link-local fallback (method=auto, link-local=4), 15s DHCP timeout, metric 100 | None — relies on NM auto-discovery | **No** — pi-gen has no wired profile; link-local fallback is NOT configured |
| **WiFi NM connection** | Created at firstboot by `nmcli`, named `preconfigured`, metric 700 | Not created (wpa_supplicant stub only) | **No** — pi-gen never creates the NM WiFi profile; wpa_supplicant.conf is a stub |
| **WiFi power save** | `wifi.powersave = 2` (disable) in `/etc/NetworkManager/conf.d/wifi-powersave.conf` | `wifi.powersaving = 2` (wrong key name) in same path | **No** — wrong NM key (`wifi.powersaving` is not valid; correct key is `wifi.powersave`) |
| **WiFi MAC randomization** | Disabled: `wifi.scan-rand-mac-address=no`, `802-11-wireless.cloned-mac-address=preserve` in `/etc/NetworkManager/conf.d/wifi-mac.conf` | Not configured | **No** — pi-gen has random MACs by default; can confuse routers/captive portals |
| **avahi / mDNS** | `avahi` + `nss-mdns` packages; avahi-daemon enabled; nsswitch.conf explicitly set to `mdns_minimal [NOTFOUND=return]` | `avahi-daemon` + `libnss-mdns` packages; avahi-daemon enabled; nsswitch.conf configured by `libnss-mdns` postinstall (automatic on Debian) | Functional match on Debian because libnss-mdns configures nsswitch.conf automatically |
| **Link-local / APIPA** | Wired NM profile: `link-local=4` (fallback after DHCP timeout) | Not configured — no wired NM profile | **No** — direct ethernet connection cannot fall back to 169.254.x.x |
| **DHCP timeout on wired** | 15 seconds (`dhcp-timeout=15` in NM connection) | NM default (~45–90s) | **No** — direct-cable users wait much longer before link-local kicks in (and it never will without the profile) |
| **Route metrics** | Wired: metric 100; WiFi: metric 700 (wired preferred) | Not configured — NM assigns arbitrary metrics | **No** — if both are up, routing is non-deterministic |
| **Multi-homed routing** | `/etc/NetworkManager/dispatcher.d/90-multihome`: source-based policy routing (per-interface routing tables + ip rules) so each NIC is independently reachable | Not present | **No** — when end0 and wlan0 are both on the same subnet, one NIC's IP goes dark |
| **sysctl multihome** | `net.ipv4.conf.all.rp_filter=2`, `arp_ignore=1`, `arp_announce=2` in `/etc/sysctl.d/99-multihome.conf` | Not configured | **No** — asymmetric paths dropped; ARP flux possible |
| **WiFi check at boot** | `wifi-check.service` (systemd, `After=NetworkManager-wait-online.service`): checks if WiFi OR ethernet is up; if WiFi disconnected and no other network, starts hotspot | `rc.local` addition: `(sleep 10; /usr/lib/pistomp-wifi/wifi_check.sh) &` | **No** — see §4 for full breakdown |
| **WiFi hotspot service** | `wifi-hotspot.service`: `Type=oneshot`, `After=NetworkManager.service`, scripts in `/usr/lib/pistomp-wifi/`; enable/disable scripts use NM `pistomp-hotspot` connection | Same service file structure, but `After=network.target` (not NM); scripts from pi-stomp repo (different logic — creates `Hotspot` not `pistomp-hotspot`); no `Type=oneshot` | **No** — multiple differences; see §4 |
| **Hotspot: ethernet-aware** | `wifi-check.sh` skips hotspot if any ethernet is connected (`grep -qE '^(ethernet|wifi-p2p):connected'`) | `wifi_check.sh` uses `iwgetid` (only checks WiFi association, ignores ethernet) | **No** — pi-gen starts hotspot even when ethernet is plugged in |
| **Hotspot: connection name** | `pistomp-hotspot` | `Hotspot` | Different — disabling the wrong name in `disable_wifi_hotspot.sh` |
| **Hotspot: idempotent** | Checks if `pistomp-hotspot` connection exists before adding; modifies if exists | Always adds a new `Hotspot` connection (no existence check) | **No** — accumulates orphan connections across reboots |
| **dnsmasq** | NM manages dnsmasq as its internal DNS cache (NM spawns it) | `dnsmasq` package installed standalone, then disabled at firstboot (`systemctl disable --now dnsmasq.service`) | Functional match (NM still uses its own dnsmasq fork), but pi-gen's explicit disable is noise |
| **hostapd** | Installed (`hostapd` package), managed by NM in AP mode | NM manages AP; legacy `disable_wifi_hotspot.sh` runs `systemctl stop hostapd` (hostapd likely not even running) | Minor noise in pi-gen's disable script |
| **hostname / mDNS name** | `pistomp.local` via avahi advertising hostname | `pistomp.local` via avahi | Match |
| **WiFi country** | Set via `modprobe.d/cfg80211.conf` at firstboot; `iw reg set` | Set via `raspi-config do_wifi_country` at build time (if `WPA_COUNTRY` set), else WiFi rf-killed | Partial — pi-gen doesn't update country at firstboot when user edits `pistomp.conf` (because pistomp.conf firstboot isn't implemented yet) |

---

## 2. Interface naming

### pistomp-arch

Arch Linux uses predictable network interface names by default (`wld0` for WiFi, `end0` for ethernet on RPi). pi-stomp's Python code hardcodes `wlan0`, so `02-system.sh` adds a udev rule:

```
# /etc/udev/rules.d/70-wifi-name.rules
SUBSYSTEM=="net", ACTION=="add", ENV{DEVTYPE}=="wlan", NAME="wlan0"
```

This renames WiFi to `wlan0`. Ethernet remains `end0` (the Arch predictable name for the built-in NIC). The NM wired profile targets `interface-name=end0`.

### pi-gen-pistomp

RPi OS Debian uses predictable names by default since Debian bullseye, but the pi-gen stage1 net-tweaks script runs:

```bash
raspi-config nonint do_net_names 1
```

`do_net_names 1` **disables** predictable names (sets `net.ifnames=0` in cmdline.txt), so the kernel falls back to classic names: WiFi is `wlan0`, ethernet is `eth0`. No udev rule is needed.

### Impact

- WiFi interface naming: both end up as `wlan0` — **match**
- Ethernet interface naming: **mismatch** — pistomp-arch uses `end0`, pi-gen uses `eth0`
  - The NM wired connection profile in pistomp-arch targets `interface-name=end0`; pi-gen would need `interface-name=eth0`
  - Any networking scripts (e.g., `nm-dispatcher-multihome`) that reference `end0` must use `eth0` in pi-gen

---

## 3. Link-local / direct connection

### pistomp-arch

Handled entirely by the NM wired connection profile (`/etc/NetworkManager/system-connections/wired-end0.nmconnection`):

```ini
[ipv4]
method=auto
link-local=4
route-metric=100
dhcp-timeout=15
```

- `method=auto`: tries DHCP first
- `link-local=4`: fallback mode — if DHCP times out after 15 seconds, NM assigns a 169.254.x.x address automatically
- `route-metric=100`: wired is strongly preferred over WiFi (metric 700)
- `dhcp-timeout=15`: shortens the wait from the NM default (~45–90s) so direct-cable users get a 169.254 address in ~15s

With both ethernet and WiFi up, the `90-multihome` dispatcher script (source-based policy routing) ensures each NIC independently responds to connections on its own IP — even when both are on the same subnet.

### pi-gen-pistomp

**No wired NM connection profile exists.** NM will auto-detect the ethernet interface but use its default behavior:
- DHCP timeout: 45–90 seconds (NM compile-time default)
- No link-local fallback configured — `link-local` defaults to `0` (disabled) in NM unless explicitly set
- No metric assigned

**Result:** When plugged into a router, the Pi will get DHCP and `pistomp.local` will work eventually. When plugged directly into a laptop (no DHCP server), the Pi will wait the full default timeout and then **fail** — no 169.254.x.x address is assigned, no mDNS advertisement for `pistomp.local`, direct connection does not work.

Also: no multihome dispatcher, so when both ethernet and WiFi are on the same LAN subnet, one of the interfaces' IPs will be unreachable.

### mDNS / avahi

Both systems install avahi-daemon and the NSS mdns module. On Arch, `nss-mdns` requires an explicit `nsswitch.conf` edit (done in `02-system.sh`). On Debian, `libnss-mdns` automatically patches `nsswitch.conf` during postinstall. So mDNS itself works in both — `pistomp.local` resolves — but only works for the direct connection case if the Pi actually has an address to advertise.

---

## 4. WiFi configuration and hotspot fallback

### pistomp-arch: full path

1. **Image build time:** No WiFi credentials baked in. No wpa_supplicant stub.
2. **Boot partition:** `/boot/pistomp.conf` (FAT32, editable after flash) contains `WIFI_SSID` / `WIFI_PASSWORD` / `WIFI_COUNTRY` variables.
3. **Firstboot (`firstboot.sh`):** Sources `pistomp.conf`; if `WIFI_SSID` is set, runs:
   ```bash
   nmcli connection delete "preconfigured" 2>/dev/null || true
   nmcli connection add type wifi ifname wlan0 con-name "preconfigured" \
       ssid "${WIFI_SSID}" \
       wifi-sec.key-mgmt wpa-psk wifi-sec.psk "${WIFI_PASSWORD}" \
       ipv4.route-metric 700 ipv6.route-metric 700 \
       connection.autoconnect yes
   ```
   Sets WiFi country via `modprobe.d/cfg80211.conf` and `iw reg set`.
4. **Boot-time check (`wifi-check.service`):** Runs after `NetworkManager-wait-online.service`:
   - If WiFi is connected: logs success, exits
   - If no WiFi but ethernet or wifi-p2p is connected: logs "skipping hotspot", exits
   - Otherwise: starts `wifi-hotspot.service`
5. **Hotspot (`enable_wifi_hotspot.sh`):** Creates or modifies NM connection `pistomp-hotspot` (AP mode, SSID `pistomp`, WPA2 `pistompwifi`, `ipv4.method shared`), then brings it up. Idempotent.
6. **Hotspot teardown (`disable_wifi_hotspot.sh`):** `nmcli connection down pistomp-hotspot`.

### pi-gen-pistomp: full path

1. **Image build time:** `stage2/02-net-tweaks` installs a stub `wpa_supplicant.conf` (empty credentials). NM NetworkManager.conf is patched to add `dns=dnsmasq`. `wifi-powersave.conf` is installed with wrong key name.
2. **Boot partition:** No `pistomp.conf`. WiFi setup is expected to happen via RPi Imager 1.x mechanism (`userconf.txt`), which doesn't work with Imager 2.x.
3. **Firstboot (`firstboot.sh`):** Switches `config.txt` to RT kernel, copies ALSA state, detects Pi model. **Does not configure WiFi at all** — it assumes WiFi was already configured by the Imager.
4. **rc.local addition (stage3/01-pistomp/01-run.sh):**
   ```bash
   sudo iw dev wlan0 set power_save off
   (sleep 10; /usr/lib/pistomp-wifi/wifi_check.sh) &
   ```
   This runs the WiFi check as a background process with a 10-second sleep.
5. **wifi_check.sh (from pi-stomp repo):** Uses `iwgetid -r` to test WiFi association:
   - If associated: logs success
   - If **not** associated: runs `sudo systemctl restart wifi-hotspot.service` — starts hotspot **even if ethernet is plugged in**
6. **Hotspot (`enable_wifi_hotspot.sh` from pi-stomp repo):** Creates `Hotspot` connection (not `pistomp-hotspot`), then `nmcli connection up Hotspot`. Not idempotent — always calls `nmcli connection add` without checking existence. Sets `ipv4.addresses 172.24.1.1/24` and `ipv4.gateway 172.24.1.1` explicitly. Restarts avahi-daemon after 15s in background.
7. **Hotspot teardown (`disable_wifi_hotspot.sh`):** `nmcli connection down Hotspot && nmcli connection delete Hotspot`, then stops `hostapd` and `dnsmasq` (likely no-ops since NM manages them).

### Key problems in pi-gen's hotspot path

- **`wifi-hotspot.service` is never enabled** in pi-gen. Stage3 installs the service file to `/usr/lib/systemd/system/` but never symlinks it into a `.wants/` directory. The `wifi_check.sh` calls `systemctl restart wifi-hotspot.service` — this will work only because NM manages the AP, but the unit isn't enabled for auto-start.
- **rc.local is fragile**: the `(sleep 10; ...) &` approach is a race against NM settling. `wifi-check.service` in pistomp-arch correctly declares `After=NetworkManager-wait-online.service`.
- **Ethernet-blind check**: `iwgetid` only checks WiFi association. A user plugged into ethernet with no WiFi configured will have the hotspot started on top of their ethernet session.
- **Connection name inconsistency**: `wifi-hotspot.service` calls `enable_wifi_hotspot.sh` which creates `Hotspot`; `disable_wifi_hotspot.sh` tears down `Hotspot`. But stage2's `wifi-hotspot.service` is a different copy from stage3's (which comes from the pi-stomp repo). If both are installed, the stage3 version wins (installed later).

---

## 5. Specific changes needed in pi-gen-pistomp

### Change 1: Fix the `wifi-powersave.conf` key name

**File:** `stage2/05-pistomp/files/wifi-powersave.conf`

**Current:**
```ini
[connection]
wifi.powersaving = 2
```

**Fix:**
```ini
[connection]
wifi.powersave = 2
```

`wifi.powersaving` is not a valid NM key. The correct key is `wifi.powersave`. Verify with `nmcli connection show <wifi-con> | grep powersave` on a working device.

---

### Change 2: Add a wired ethernet NM connection profile with link-local fallback

**File to create:** `stage2/05-pistomp/files/wired-eth0.nmconnection`

```ini
[connection]
id=wired-eth0
type=ethernet
interface-name=eth0
autoconnect=true

[ipv4]
method=auto
link-local=4
route-metric=100
dhcp-timeout=15

[ipv6]
method=link-local
```

**Install it in `stage2/05-pistomp/03-run.sh`** (or a new `05-run.sh`):

```bash
install -d -m 700 "${ROOTFS_DIR}/etc/NetworkManager/system-connections"
install -m 600 files/wired-eth0.nmconnection \
    "${ROOTFS_DIR}/etc/NetworkManager/system-connections/"
```

Note: the interface name is `eth0` (not `end0`) because pi-gen disables predictable names via `raspi-config do_net_names 1`.

This change alone fixes the direct-connection (169.254.x.x) use case.

---

### Change 3: Add WiFi MAC randomization disable config

**File to create:** `stage2/05-pistomp/files/wifi-mac.conf`

```ini
[device]
wifi.scan-rand-mac-address=no

[connection]
802-11-wireless.cloned-mac-address=preserve
```

**Install in `stage2/05-pistomp/03-run.sh`:**

```bash
install -Dm 644 files/wifi-mac.conf \
    "${ROOTFS_DIR}/etc/NetworkManager/conf.d/wifi-mac.conf"
```

---

### Change 4: Replace the NM.conf patch with a direct write

**Current approach:** `03-run.sh` applies `NetworkManager.conf.diff` with `patch`. This is fragile — if the upstream NM.conf format changes or the file has already been patched, `patch` fails.

**Fix in `stage2/05-pistomp/03-run.sh`**: replace the `patch` call with a direct write:

```bash
cat > "${ROOTFS_DIR}/etc/NetworkManager/NetworkManager.conf" <<'EOF'
[main]
dns=dnsmasq
plugins=keyfile

[keyfile]
unmanaged-devices=none
EOF
```

Also drop the `ifupdown` plugin (not needed — Debian uses keyfile with NM for the pistomp use case) and set `unmanaged-devices=none` to ensure NM manages all interfaces.

Delete `stage2/05-pistomp/files/NetworkManager.conf.diff` once this is done.

---

### Change 5: Replace rc.local wifi check with a systemd service

**Current:** Stage3 appends to `/etc/rc.local`:
```bash
sudo iw dev wlan0 set power_save off
(sleep 10;/usr/lib/pistomp-wifi/wifi_check.sh) &
```

**Fix:** Remove the rc.local addition from `stage3/01-pistomp/01-run.sh` (lines 65–72). Instead:

**a. Create `stage2/05-pistomp/files/services/wifi-check.service`:**

```ini
[Unit]
Description=Check WiFi and start hotspot if disconnected
After=NetworkManager-wait-online.service
Wants=NetworkManager-wait-online.service

[Service]
Type=oneshot
ExecStartPre=/bin/sleep 10
ExecStart=/usr/lib/pistomp-wifi/wifi-check.sh

[Install]
WantedBy=multi-user.target
```

**b. Create `stage2/05-pistomp/files/wifi-check.sh`** (new file, replacing the pi-stomp repo's `wifi_check.sh`):

```bash
#!/bin/bash
# Check WiFi connectivity and fall back to hotspot if disconnected.
LOG="/var/log/wifi.log"
TIMESTAMP=$(date '+%F_%H:%M:%S')

if nmcli -t -f TYPE,STATE device | grep -q '^wifi:connected'; then
    echo "${TIMESTAMP} Wifi is connected." >> "$LOG"
elif nmcli -t -f TYPE,STATE device | grep -qE '^(ethernet|wifi-p2p):connected'; then
    echo "${TIMESTAMP} Wifi not connected, but another network is up. Skipping hotspot." >> "$LOG"
else
    systemctl start wifi-hotspot.service
    echo "${TIMESTAMP} Wifi not connected. Starting hotspot." >> "$LOG"
fi
```

Key improvement: checks ethernet status before starting the hotspot. Install this from `stage2/05-pistomp/` so it's in the image regardless of the pi-stomp repo state.

**c. Install and enable in `stage2/05-pistomp/01-run.sh`:**

```bash
install -m 644 files/services/wifi-check.service /usr/lib/systemd/system/
install -m 755 files/wifi-check.sh /usr/lib/pistomp-wifi/wifi-check.sh
ln -sf /usr/lib/systemd/system/wifi-check.service \
    /etc/systemd/system/multi-user.target.wants/wifi-check.service
```

**d. In `stage3/01-pistomp/01-run.sh`**, remove lines 65–72 (the rc.local addition). Stop installing `wifi_check.sh` from the pi-stomp repo (line 46) since we now ship our own version.

---

### Change 6: Fix the hotspot scripts (use `pistomp-hotspot` not `Hotspot`)

The scripts coming from the pi-stomp repo use connection name `Hotspot`. pistomp-arch uses `pistomp-hotspot`. Align pi-gen with pistomp-arch's naming and logic.

**Replace `enable_wifi_hotspot.sh`** (install from `stage2/05-pistomp/files/` rather than pulling from pi-stomp repo at stage3):

```bash
#!/bin/bash
set -e
SSID="pistomp"
PASSWORD="pistompwifi"
IFACE="wlan0"

if ! nmcli connection show "${SSID}-hotspot" &>/dev/null; then
    nmcli connection add type wifi ifname "${IFACE}" con-name "${SSID}-hotspot" \
        autoconnect no ssid "${SSID}" mode ap \
        -- wifi-sec.key-mgmt wpa-psk wifi-sec.psk "${PASSWORD}" \
        ipv4.method shared
else
    nmcli connection modify "${SSID}-hotspot" \
        802-11-wireless.mode ap \
        802-11-wireless-security.key-mgmt wpa-psk \
        802-11-wireless-security.psk "${PASSWORD}" \
        ipv4.method shared
fi

nmcli connection up "${SSID}-hotspot"
```

**Replace `disable_wifi_hotspot.sh`:**

```bash
#!/bin/bash
nmcli connection down "pistomp-hotspot" 2>/dev/null || true
```

**Update `wifi-hotspot.service`** (`stage2/05-pistomp/files/services/wifi-hotspot.service`):

```ini
[Unit]
Description=WiFi Hotspot
After=NetworkManager.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/lib/pistomp-wifi/enable_wifi_hotspot.sh
ExecStop=/usr/lib/pistomp-wifi/disable_wifi_hotspot.sh

[Install]
WantedBy=multi-user.target
```

Changes from pi-gen's current version: add `Type=oneshot` (without it, RemainAfterExit behaves oddly for a oneshot); change `After=network.target` → `After=NetworkManager.service` so NM is actually ready.

**In `stage3/01-pistomp/01-run.sh`**, stop installing the hotspot scripts from the pi-stomp repo (lines 43–48). We now ship them from `stage2/05-pistomp/files/` instead. Keep the wifi-hotspot.service install from stage2 (it's already installed by `01-run.sh` from `stage2/05-pistomp`).

---

### Change 7: Enable wifi-hotspot.service

`wifi-hotspot.service` is installed to `/usr/lib/systemd/system/` by stage3 but never enabled (no `.wants/` symlink). The `wifi-check.sh` starts it on demand via `systemctl start`, which works fine without the service being enabled. However, the `[Install]` section's `WantedBy=multi-user.target` implies it could auto-start — that should NOT happen. Leave it NOT enabled (install-only), which is what both repos currently do.

No change needed here — just clarifying it's intentional.

---

### Change 8: Add multihome routing dispatcher (optional but recommended)

This fixes the case where both ethernet and WiFi are on the same LAN subnet. Not strictly required for the three primary use cases (they use different subnets: 169.254.x.x for direct, LAN DHCP for router, hotspot subnet for WiFi AP). But without it, users who plug in ethernet while on WiFi on the same router subnet will see one interface go dark.

**File to create:** `stage2/05-pistomp/files/nm-dispatcher-multihome`

Copy from `../pistomp-arch/files/nm-dispatcher-multihome`, **but change `end0` to `eth0`** throughout:

```bash
case "$IFACE" in
    eth0)  TABLE=100 ;;
    wlan0) TABLE=200 ;;
    *)     exit 0 ;;
esac
```

**Install in `stage2/05-pistomp/03-run.sh`:**

```bash
install -Dm 755 files/nm-dispatcher-multihome \
    "${ROOTFS_DIR}/etc/NetworkManager/dispatcher.d/90-multihome"
ln -sf /usr/lib/systemd/system/NetworkManager-dispatcher.service \
    "${ROOTFS_DIR}/etc/systemd/system/dbus-org.freedesktop.nm-dispatcher.service"
```

---

### Change 9: Add sysctl multihome settings

**File to create:** `stage2/05-pistomp/files/99-multihome.conf`

```
net.ipv4.conf.all.rp_filter = 2
net.ipv4.conf.default.rp_filter = 2
net.ipv4.conf.all.arp_ignore = 1
net.ipv4.conf.default.arp_ignore = 1
net.ipv4.conf.all.arp_announce = 2
net.ipv4.conf.default.arp_announce = 2
```

**Install in `stage2/05-pistomp/03-run.sh`:**

```bash
install -Dm 644 files/99-multihome.conf \
    "${ROOTFS_DIR}/etc/sysctl.d/99-multihome.conf"
```

---

### Change 10: WiFi credential setup at firstboot (if implementing pistomp.conf)

If/when `pistomp.conf` firstboot is implemented (described in `UX-PARITY.md` §4), the WiFi connection creation must include route metrics to match pistomp-arch:

```bash
nmcli connection add type wifi ifname wlan0 con-name "preconfigured" \
    ssid "${WIFI_SSID}" \
    wifi-sec.key-mgmt wpa-psk wifi-sec.psk "${WIFI_PASSWORD}" \
    ipv4.route-metric 700 ipv6.route-metric 700 \
    connection.autoconnect yes
```

The `ipv4.route-metric 700` ensures the wired connection (metric 100) is always preferred over WiFi when both are available.

Also set the WiFi country:

```bash
printf 'options cfg80211 ieee80211_regdom=%s\n' "${WIFI_COUNTRY:-US}" \
    > /etc/modprobe.d/cfg80211.conf
iw reg set "${WIFI_COUNTRY:-US}" 2>/dev/null || true
```

---

## Summary of priority

| # | Change | Fixes use case | Effort |
|---|---|---|---|
| 2 | Wired NM connection profile with link-local fallback | Direct connection (169.254.x.x) | Low |
| 1 | Fix `wifi.powersave` key name | WiFi power management | Trivial |
| 5 | Replace rc.local wifi check with systemd service | Hotspot not starting over ethernet | Low |
| 6 | Fix hotspot scripts (naming, idempotency) | Hotspot reliability | Low |
| 4 | Replace NM.conf patch with direct write | Robustness | Low |
| 3 | WiFi MAC randomization disable | Router/captive portal compat | Trivial |
| 8+9 | Multihome dispatcher + sysctl | Dual ethernet+wifi on same subnet | Medium |
| 10 | WiFi metric in firstboot | Wired-preferred routing | Low (part of pistomp.conf work) |
