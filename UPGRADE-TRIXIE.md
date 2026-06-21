# Upgrade to Raspberry Pi OS Trixie (Debian 13)

Engineer's checklist for upgrading `pi-gen-pistomp` from `RELEASE=bookworm` to `RELEASE=trixie`.

---

## 1. Latest release

**Image:** `2026-06-18-raspios-trixie-arm64-lite.img.xz`  
**Directory:** `raspios_lite_arm64-2026-06-19/`  
**Kernel:** Linux 6.18.34 (commit `c8c7494100e99ee05b11aaa4f0588a223a63d1af`)  
**Python:** 3.13.5 (package `python3 3.13.5-1`, `libpython3.13 3.13.5-2+deb13u2`)  
**pi-gen commit:** `ca8aeed0ae300c2a89f55ce9617d5f96a27e99e5`  
**Trixie first release:** 2025-10-01

Notable changes since bookworm's last release that affect us:
- Debian 13 base (trixie) as of 2025-10-01
- Python 3.13 as system default (was 3.11)
- `python3-flask` removed from 2026-06-18 desktop release (irrelevant for lite)
- `Pulseaudio` removed (not our concern)
- Passwordless sudo disabled by default as of 2026-04-13 — check firstboot scripts

---

## 2. Is `raspios_lite_arm64` the right base?

**Yes.** `raspios_lite_arm64` is the correct base: headless, no desktop, minimal footprint (~500 MB compressed). There is no separate "headless" variant — lite **is** the headless product. The desktop and full images add ~1–2 GB of GUI tooling we don't need.

The 64-bit (arm64) image is required because:
- Pi 5 only runs 64-bit
- Our RT kernel `.deb` files are `arm64` packages
- The build already targets arm64 (see `linux-image-6.1.54-rt15-v8+` and `linux-image-6.12.9-v8-16k+`)

---

## 3. Checklist

### 3.1 `config` — one-line change

```diff
-RELEASE=bookworm
+RELEASE=trixie
```

That's it for the config file. Everything else is in the scripts.

---

### 3.2 `stage2/04-python/01-run.sh` — Python 3.13 breakage

#### EXTERNALLY-MANAGED path (line 6)

```bash
# Current — wrong on trixie:
rm -rf /usr/lib/python3.11/EXTERNALLY-MANAGED

# Fix:
rm -rf /usr/lib/python3.13/EXTERNALLY-MANAGED
```

#### `tornado==4.3` — not a problem if mod-ui runs in a Python 3.11 venv

`tornado 4.x` is incompatible with Python 3.12+ (removed `collections.MutableMapping`, broken `asyncio.get_event_loop()` behaviour). mod-ui also uses `@gen.engine` and `gen.Task(...)` patterns removed in tornado 6, so upgrading tornado is not a drop-in fix.

**The correct solution is the same one used by pistomp-arch: run mod-ui in its own uv-managed Python 3.11 venv, independent of the system Python.** uv can download and manage Python versions without pyenv:

```bash
# During image build (in chroot):
uv python install 3.11
uv venv --python 3.11 /opt/pistomp/venvs/mod-ui
UV_PROJECT_ENVIRONMENT=/opt/pistomp/venvs/mod-ui uv pip install tornado==4.5.3 ...
```

This means:
- **mod-ui, browsepy, touchosc2midi** → Python 3.11 venvs managed by uv (tornado-compatible, no porting work)
- **pi-stomp** → system Python 3.13 with `--system-site-packages` (accesses `python3-lgpio`, `python3-lilv`, etc.)

The global `pip3 install tornado==4.3` line in `04-python/01-run.sh` should be removed entirely — tornado is a per-venv dependency, not a system package.

`tornado==4.5.3` (latest 4.x) is preferred over 4.3 as it has minor Python 3.x fixes. Pin it in the mod-ui venv install, not globally.

#### `netifaces==0.10.5` — broken on Python 3.12+

`netifaces 0.10.5` (2019) fails to build from source on Python 3.12+ due to removed C APIs. Replace with `netifaces2` (maintained fork, latest 0.0.22, `requires_python: >=3.6`):

```diff
-pip3 install netifaces==0.10.5
+pip3 install netifaces2
```

Check whether anything imports `netifaces` — if so, `netifaces2` is a drop-in replacement.

#### `pystache==0.5.4` — outdated pin, needs bumping

`pystache 0.5.4` requires Python `>=3.8` (no upper bound), but there are known issues in 3.12+. Latest is `0.6.8` which explicitly supports 3.8+. Drop the pin:

```diff
-pip3 install pyserial==3.0 pystache==0.5.4 aggdraw==1.3.11 scandir backports.shutil-get-terminal-size
+pip3 install pyserial==3.5 pystache aggdraw scandir backports.shutil-get-terminal-size
```

Actually, `aggdraw 1.3.11` can also be dropped (latest is `1.4.1`, `requires_python: >=3.11`), and `Pillow==9.4.0` needs upgrading (latest `12.2.0`, requires Python `>=3.10`):

```diff
-pip3 install Pillow==9.4.0
+pip3 install Pillow
```

#### Packages that can be dropped entirely

- `scandir` — stdlib since Python 3.5 (`os.scandir`). Installing from PyPI is a no-op on 3.x.
- `backports.shutil-get-terminal-size` — stdlib since Python 3.3. Same situation.
- `python-config` — this appears to be a tiny shim; confirm it's still needed.
- `pep8` — deprecated alias for `pycodestyle`. Drop or replace.
- `sphinx`, `flake8`, `coverage`, `pep8` — developer tools with no runtime use in a production image. Remove all four to save space and build time.

#### `mido==1.1.24` — outdated pin

Latest mido is `1.3.3` (`~=3.7`). Drop the pin:

```diff
-pip3 install mido==1.1.24
+pip3 install mido
```

#### `cython` — version matters for Python 3.13

Trixie ships Cython 3.x which is incompatible with some packages (previously documented for `pyliblo`/touchosc2midi). If cython is still needed here for building C extensions, test carefully. Trixie's apt package `cython3` provides Cython 3.

#### `python3-rpi.gpio` removal (lines 33–37)

The current code removes `python3-rpi.gpio` and installs `python3-rpi-lgpio`. On trixie:
- `python3-rpi.gpio 0.7.1` is **still present** in Debian trixie
- `python3-rpi-lgpio 0.6-0~rpt1+trixie` is available from the **RPi archive** (`archive.raspberrypi.com`)
- The swap-and-remove logic still applies

However, the `python3-rpi.gpio` package is now listed in `stage2/01-sys-tweaks/00-packages` — that's where the initial install happens. The `04-python/01-run.sh` cleanup is a secondary fix. Both need to be checked for consistency.

---

### 3.3 `stage2/05-pistomp/02-run.sh` — build script breakage

#### lilv `--pythondir` hardcodes Python 3.11 (line 38)

```bash
# Current:
./waf configure --prefix=/usr/local --no-utils --no-bash-completion --pythondir=/usr/local/lib/python3.11/dist-packages

# Fix:
./waf configure --prefix=/usr/local --no-utils --no-bash-completion --pythondir=/usr/local/lib/python3.13/dist-packages
```

**Better yet**: trixie ships `liblilv-dev 0.24.26-1` and `python3-lilv 0.24.26-1` via apt (up from 0.24.12 which we build from source). This means we can **stop building lilv from source entirely** and use:

```bash
apt-get install -y liblilv-dev python3-lilv
```

This eliminates the waf build step for lilv, the hardcoded pythondir, and the wget of the tarball. Verify that `lilv 0.24.26` is compatible with whatever mod-host/mod-ui version we're running before dropping the source build.

#### lilv waf version

`lilv 0.24.12` bundles an old `waf` (circa 2012–2013). Old waf uses Python internals removed in Python 3.12+ (specifically `imp` module was removed in 3.12). This is another reason to prefer the apt package over building from source.

#### tornado `sed` patch (line 64) is wrong for Python 3.13

```bash
# Current — wrong path on trixie:
sed -i -e 's/collections.MutableMapping/collections.abc.MutableMapping/' /usr/local/lib/python3.11/dist-packages/tornado/httputil.py
```

Path changes to `python3.13`, but more importantly this patch is insufficient for Python 3.13 — see the tornado section above. If you're switching to the apt `python3-tornado`, this line should be removed entirely.

#### jack2 `waf configure` — Python 3.13 compatibility

`jack2 v1.9.22` bundles its own waf (`#!/usr/bin/python3` in the `waf` script header). The bundled waf in jack2 v1.9.22 is newer than lilv's and should handle Python 3.13 (the waf project has maintained 3.x compatibility). Test this but it's lower risk.

**Better yet**: trixie ships `jackd2 1.9.22~dfsg-4` via apt — the exact same version we build from source. Consider switching to the system package:

```bash
apt-get install -y jackd2 libjack-jackd2-dev
```

This eliminates the ~10-minute jack2 source build. Verify `jack-example-tools` is still needed if jackd2 comes from apt.

#### `browsepy` — install from micahvdm fork, Python version unknown

`browsepy` from `https://github.com/micahvdm/browsepy.git` is installed via `pip3 install ./`. The upstream `browsepy 0.5.6` has no declared `requires_python`. Test on Python 3.13 — if it fails, the fix is likely in the flask/werkzeug dependency versions it pins.

---

### 3.4 `stage2/05-pistomp/03-run.sh` — RT kernel `.deb` files

The three kernel `.deb` files in `files/sys/` are pre-built Debian packages:
- `linux-image-6.1.54-rt15-v8+_6.1.54-rt15-v8+-2_arm64.deb`
- `linux-headers-6.1.54-rt15-v8+_6.1.54-rt15-v8+-2_arm64.deb`
- `linux-libc-dev_6.1.54-rt15-v8+-2_arm64.deb`
- `linux-image-6.12.9-v8-16k+_6.12.9-ga20d400dff3d-3_arm64.deb`

These are installed with `dpkg -i` inside chroot — they don't interact with the Debian release at the package level. However:

- These `.deb` files were built against a **bookworm kernel infrastructure** (ABI, initramfs hooks). On trixie, `initramfs-tools` and `linux-base` may differ, which can cause `dpkg -i` to fail or produce a broken initramfs.
- The trixie base image ships **Linux 6.18.34** — significantly newer than the 6.1.54 RT kernel. Module ABI compatibility between the two needs to be verified.
- **`linux-image-6.12.9-v8-16k+`** is closer to the trixie base kernel (6.12/6.18 gap is smaller) and is less likely to have initramfs issues.

**Action required:** Rebuild the RT kernel `.deb` files targeting trixie's packaging infrastructure before committing to an upgrade. The `pistomp-arch` repo has `build-rt-kernel-docker.sh` as a reference for how this is done; adapt for Debian packaging.

Also, line 50 in `03-run.sh` downloads `midi-uart0-pi5.dtbo` from the firmware repo — verify the URL is still valid and the overlay is compatible with kernel 6.18.

---

### 3.5 `stage2/01-sys-tweaks/00-packages` — broken package names

The package list in `stage2/01-sys-tweaks/00-packages` references several packages that **do not exist in trixie** (Debian or RPi archive):

| Package | Status in trixie | Replacement |
|---|---|---|
| `pigpio` | **REMOVED** — not in Debian 13, not in RPi trixie archive | Use `liblgpio1`/`liblgpio-dev` (RPi archive) |
| `python3-pigpio` | **REMOVED** | Use `python3-lgpio` (RPi archive) |
| `raspi-gpio` | **REMOVED** | Use `python3-gpiozero` (already in list) |
| `python3-rpi.gpio` | Still present in trixie Debian (0.7.1) but should be replaced | `python3-rpi-lgpio` from RPi archive |
| `policykit-1` | **REMOVED** — renamed to `polkit` in Debian 12+ | `polkit` |
| `rcconf` | **REMOVED** from Debian 13 | Nothing needed; `systemctl enable/disable` is used directly |
| `libfluidsynth2` | **REMOVED** — only `libfluidsynth3` in trixie | `libfluidsynth3` |
| `rpi-update` | Available in RPi trixie archive | No change needed |

**Changes to `00-packages`:**

```diff
-pigpio python3-pigpio raspi-gpio python3-rpi.gpio
+python3-lgpio python3-rpi-lgpio python3-gpiozero
 ...
-policykit-1
+polkit
 ...
-dnsmasq iptables python3-smbus liblo-dev python3-liblo libzita-alsa-pcmi-dev authbind rcconf libfluidsynth-dev lockfile-progs
+dnsmasq iptables python3-smbus liblo-dev python3-liblo libzita-alsa-pcmi-dev authbind libfluidsynth-dev lockfile-progs
-libfluidsynth2
+libfluidsynth3
```

Note: `python3-rpi-lgpio` comes from the RPi archive (`archive.raspberrypi.com/debian trixie main`), not the Debian main archive. Ensure the RPi apt source is added before this package is requested.

---

### 3.6 `stage2/04-python/01-run.sh` — rpi.gpio removal lines

Lines 33–37:
```bash
sudo apt-get -y remove python3-rpi.gpio
sudo apt-get -y install python3-rpi-lgpio
sudo apt install python3-rpi-lgpio
```

If `python3-rpi.gpio` is removed from `00-packages` (above), this secondary removal is redundant but harmless. Clean it up. The double `apt install` on lines 35–36 is also a pre-existing redundancy.

---

### 3.7 `stage3/00-env/01-run.sh` — uv install

`uv` is installed by downloading from `astral.sh`. This is version-independent and should continue to work on trixie. No changes needed.

---

### 3.8 `stage3/01-pistomp/01-run.sh` — venv creation

Line 21:
```bash
/usr/local/bin/uv venv --python /usr/bin/python3 --system-site-packages /opt/pistomp/venvs/pi-stomp
```

On trixie, `/usr/bin/python3` will be Python 3.13. The `--system-site-packages` flag means the venv inherits `python3-lilv`, `python3-lgpio`, `python3-smbus2`, etc. from the system. This approach is correct and no change is needed **IF** all the system packages exist with the right names (see 3.5 above).

The `uv sync` in `02-run.sh` runs against `pi-stomp`'s `pyproject.toml`. Verify that `pi-stomp`'s declared dependencies are compatible with Python 3.13 — specifically any GPIO or hardware libraries pinned in the pyproject.

---

### 3.9 `stage2/00-dummy-packages/` — `jack-dummy` equivs package

`equivs 2.3.2` is in trixie Debian. The `equivs-build` approach still works.

The `jack-dummy` package provides `libjack-jackd2-0`, `libjack-jackd2-dev`, `jackd2`. If you switch to using the apt `jackd2` package (see 3.3), remove this dummy package entirely — it would conflict with the real jackd2.

If keeping the source build of jack2, the dummy package is still needed exactly as before.

---

### 3.10 Service files — authbind, mod-ui

`authbind 2.2.0` is present in trixie. The `mod-ui.service` approach (`ExecStart=/usr/bin/authbind /usr/local/bin/mod-ui`) still works. No changes to service files needed for the authbind approach.

---

### 3.11 `stage3/01-pistomp/01-run.sh` — usbmount

Line 51:
```bash
dpkg -i /home/${FIRST_USER_NAME}/pi-stomp/setup/services/usbmount.deb
```

`usbmount` is **not in trixie Debian** at all (removed after bullseye). The bundled `.deb` in the pi-stomp repo was presumably built for buster/bullseye. It will fail `dpkg -i` on trixie due to broken dependencies.

**Options:**
- Use `udisks2` (already in `00-packages`) with a udev rule for automounting — the modern approach
- Build `usbmount` from source against trixie
- Use a udev-based automounter script (simpler, no daemon required)

This needs a fix regardless of the trixie upgrade, since the `.deb` is already bookworm-questionable.

---

## 4. Trixie features that simplify what we build from source

| Component | Current | Trixie apt | Action |
|---|---|---|---|
| `jack2` | Built from source (v1.9.22, ~10 min) | `jackd2 1.9.22~dfsg-4` | Switch to apt; same version |
| `libjack-jackd2-dev` | From source build | `libjack-jackd2-dev 1.9.22~dfsg-4` | Switch to apt |
| `lilv 0.24.12` | Built from source (~5 min) | `liblilv-dev 0.24.26-1`, `python3-lilv 0.24.26-1` | Switch to apt; newer version |
| `python3-tornado 4.3` | pip from PyPI (broken on 3.13) | `python3-tornado 6.4.2-3+deb13u2` | Switch to apt + port mod-ui |

Switching jack2 and lilv to apt packages would significantly reduce build time and eliminate two `waf`-based build steps that are fragile with newer Python versions.

---

## 5. Migration risks and what to test

### High severity

1. **tornado/mod-ui on Python 3.13** — not a blocker if mod-ui runs in a uv-managed Python 3.11 venv (same pattern as pistomp-arch). Remove the global `pip3 install tornado` from `04-python/01-run.sh` and install it into the mod-ui venv only. See §3.2 above.

2. **RT kernel `.deb` initramfs compatibility** — the 6.1.54-rt15 and 6.12.9 kernel packages were built for bookworm. On trixie they may fail to install (initramfs-tools ABI) or produce a non-booting system. This is the highest-risk hardware change.

3. **`usbmount.deb`** — will definitely fail on trixie. Needs a replacement strategy before the build can complete.

4. **`pigpio` gone** — any pi-stomp code that imports `pigpio` at runtime will fail. Verify pi-stomp's `pyproject.toml` hardware extras don't depend on it, or that `python3-lgpio` provides a compatible interface for all pi-stomp hardware paths.

### Medium severity

5. **`libfluidsynth2` → `libfluidsynth3`** — LV2 plugins linked against `libfluidsynth.so.2` will fail to load. The pre-built plugin tarball at `treefallsound.com/downloads/lv2plugins.tar.gz` was likely built against `libfluidsynth2`. Rebuild or provide a shim `.so` if needed.

6. **`netifaces` build failure** — `netifaces 0.10.5` will fail to build from source on Python 3.13 (C extension incompatibility). This is a hard build failure, not a silent runtime issue. Replace with `netifaces2` before any build attempt.

7. **`lilv 0.24.12` waf build** — old waf uses `imp` module (removed in Python 3.12). If you don't switch to the apt package, this build step will fail completely. Switching to apt `python3-lilv 0.24.26` is the correct fix.

8. **`pystache` pinned to 0.5.4** — may have silent runtime failures on Python 3.13. Unpin and take latest `0.6.8`.

### Low severity

9. **Passwordless sudo** — trixie disables it by default (release note from 2026-04-13). If any build scripts or firstboot steps use `sudo` without a password interactively, they'll hang. Audit `firstboot.sh` and the `rc.local` additions.

10. **`rm /etc/profile.d/bash_completion.sh`** (`04-run.sh` line 12) — this file may not exist or may have moved on trixie. Use `rm -f` to avoid a fatal error.

11. **`auto_initramfs=1` in `config_pistomp.txt`** — the trixie base kernel is `6.18.34` (using `linux-image-rpi-v8` meta-package). The initramfs filename convention may differ. Test that the RT kernel override (`[pi3]`/`[pi4]` sections with `os_prefix=6.1.54-rt15-v8+/`) still works with trixie's firmware.

12. **`python3-liblo` / `liblo-dev`** — both still available in trixie. No change needed.

13. **`python3-flask`** — installed via `pip3 install flask` (no pin). Flask 3.x dropped Python 3.8 but supports 3.9+, so 3.13 is fine. Remove the pin-less install if switching to `python3-flask` from apt (`3.1.1-1` in trixie).

---

## 6. Recommended upgrade sequence

1. **Fork a trixie branch.** Change `RELEASE=trixie` in `config`. Expect the build to fail — the goal is to identify failures one at a time.

2. **Fix the package list first** (`00-packages`): remove `pigpio`, `python3-pigpio`, `raspi-gpio`, `policykit-1`, `rcconf`, `libfluidsynth2`; add `polkit`, `python3-lgpio`, `libfluidsynth3`. Change `python3-rpi.gpio` → `python3-rpi-lgpio`.

3. **Fix `04-python/01-run.sh`**: update `EXTERNALLY-MANAGED` path to `3.13`, drop broken pip pins (`netifaces==0.10.5`, `tornado==4.3`, `Pillow==9.4.0`), drop redundant packages (`scandir`, `backports.shutil-get-terminal-size`, `pep8`, `sphinx`, `flake8`, `coverage`).

4. **Switch lilv and jack2 to apt** in `02-run.sh`. Remove the source build blocks and the `--pythondir=.../python3.11/...` line.

5. **Move mod-ui to a Python 3.11 venv** — `uv python install 3.11` in the chroot, then create `/opt/pistomp/venvs/mod-ui` with `--python 3.11`. Install tornado 4.5.3 and mod-ui's other deps into that venv. Remove the global `pip3 install tornado` from `04-python/01-run.sh`. Update `mod-ui.service` to use the venv Python directly instead of authbind + system Python.

6. **Address `usbmount`** — replace with a udisks2/udev approach or build from source.

7. **Rebuild RT kernel `.deb` files** against trixie packaging. This requires access to a trixie ARM environment.

8. **Run a full build and boot test** on real hardware (Pi 3, Pi 4, Pi 5 each).
