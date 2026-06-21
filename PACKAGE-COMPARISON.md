# Package Comparison: pi-gen-pistomp vs. pistomp-arch

Comparison between the Debian-based image builder (`pi-gen-pistomp`, targeting bookworm/planned trixie) and the Arch Linux ARM image builder (`pistomp-arch`, tested on hardware). Generated 2026-06-21.

**Sources read:**
- pi-gen-pistomp: `stage2/01-sys-tweaks/00-packages`, `00-packages-nr`, `stage2/02-net-tweaks/00-packages`, `stage1/01-sys-tweaks/00-packages`, `stage2/04-python/01-run.sh`, `stage2/05-pistomp/02-run.sh`, `stage2/05-pistomp/03-run.sh`, `stage3/01-pistomp/01-run.sh`, `stage3/01-pistomp/02-run.sh`, `UPGRADE-TRIXIE.md`, `PACKAGING.md`, all `files/services/*.service`, `debpkgs/sfizz-pistomp/`
- pistomp-arch: `config.sh`, all `pkgbuilds/*/PKGBUILD`, `scripts/02-system.sh`, `scripts/03-audio.sh`, `scripts/04-native-pkgs.sh`, `scripts/05-python.sh`, `patches/`, `pkgbuilds/jack2-pistomp/*.patch`, `pkgbuilds/jack_capture/*.patch`, `pkgbuilds/sfizz-pistomp/*.patch`

---

## 1. Native C Components

### JACK2

| Attribute | pi-gen-pistomp (bookworm) | pi-gen-pistomp (trixie, planned) | pistomp-arch |
|---|---|---|---|
| Version | 1.9.22 | 1.9.22 (via apt `jackd2 1.9.22~dfsg-4`) | 1.9.22 |
| Source | Git clone + waf build from source | apt | PKGBUILD: `pkgbuilds/jack2-pistomp/PKGBUILD` |
| Install prefix | `/usr/local/` | `/usr/` | `/usr/` |
| Package name | None (bare make install) | `jackd2` | `jack2-pistomp` |

**Patches in pistomp-arch, absent in pi-gen:**

1. `pkgbuilds/jack2-pistomp/pi-controller-reset.patch` — **Critical stability fix.** `JackAudioAdapterInterface::ResetRingBuffers()` never clears the PI controller integrator. Across repeated ring failures, the accumulated windup biases the resample ratio further off each cycle, causing failure rate to ramp monotonically after jackd start. The fix calls `fPIControler.OurOfBounds()` on reset, which zeroes the integral. Upstream's `OurOfBounds()` exists for this purpose but has zero callsites in 1.9.22. **pi-gen does not have this patch.**

2. `pkgbuilds/jack2-pistomp/jack2-1.9.22-db-5.3.patch` — Arch-specific: changes wscript to look for `db5.3/db.h` and `-ldb-5.3` instead of `db.h`/`-ldb`. Required because Arch ships BerkeleyDB as `db5.3`. Not applicable to Debian which uses a different name scheme for the same library.

3. **Bundled waf removal** — pistomp-arch's PKGBUILD removes the bundled waflib (`rm -rv waflib`) and builds against system waf. This fixes Python 3.12+ compatibility (bundled waf uses `imp`, removed in 3.12). This will matter to pi-gen trixie if it keeps the source build path.

**Dummy package note (pi-gen only):** `stage2/00-dummy-packages/` creates a `jack-dummy` equivs package that provides `libjack-jackd2-0`, `libjack-jackd2-dev`, `jackd2`. This is used so packages that depend on jack can be installed while jack2 itself is built from source (to avoid pulling the distro jack2 as a dependency). pistomp-arch has no equivalent because PKGBUILD's `provides=` and `conflicts=` arrays handle this cleanly via pacman's dependency system.

---

### JACK Example Tools (`jack_load`, `jack_unload`, etc.)

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Version | Branch `debian/4-4` from salsa.debian.org | System package `jack-example-tools` via pacman |
| Source | `git clone --branch debian/4-4 https://salsa.debian.org/multimedia-team/jack-example-tools.git` + meson build | `pacman -S jack-example-tools` |
| Install prefix | `/usr/local` | `/usr` |

pi-gen clones the Debian-packaged version 4 from salsa, not the upstream GitHub branch. pistomp-arch just installs from pacman. The version should be equivalent (both are version 4), but the exact package version in Arch's repo at build time is not pinned.

---

### Hylia (Ableton Link host transport)

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Version | HEAD of `https://github.com/falkTX/Hylia.git` (unpinned) | HEAD of `https://github.com/falkTX/Hylia.git` (unpinned) |
| Source | Git clone + bare `make install` into `/usr/local` | PKGBUILD: `pkgbuilds/hylia/PKGBUILD`, installs to `/usr` |
| `NOOPT` flag | `export NOOPT=true` | `make PREFIX=/usr NOOPT=true` |

Both use the same flag (`NOOPT=true`) and the same repo. No patches in either. The only difference is the install prefix (`/usr/local` vs `/usr`) and that pistomp-arch tracks the install via pacman.

---

### lilv

| Attribute | pi-gen-pistomp (bookworm) | pi-gen-pistomp (trixie, planned) | pistomp-arch |
|---|---|---|---|
| Version | 0.24.12 | 0.24.26 (via apt `liblilv-dev 0.24.26-1`, `python3-lilv 0.24.26-1`) | System package via pacman: `lilv python-lilv` (Arch ships 0.24.26 or later) |
| Source | wget tarball + waf build from source | apt | `pacman -S lilv python-lilv` |
| Python bindings | `--pythondir=/usr/local/lib/python3.11/dist-packages` | `/usr/lib/python3/dist-packages` (via apt) | `python-lilv` pacman package |
| LV2 support libs | `libserd-dev`, `libsord-dev`, `libsratom-dev` in `00-packages-nr` | Same (from apt) | `serd sord sratom lv2` via pacman |

**Version divergence flagged:** pi-gen bookworm uses 0.24.12 (2021 source tarball), while pistomp-arch and trixie both use 0.24.26. If mod-host or mod-ui rely on APIs added between 0.24.12 and 0.24.26, this could cause subtle runtime failures in pi-gen bookworm.

**trixie waf breakage:** `lilv 0.24.12`'s bundled waf uses the `imp` module removed in Python 3.12. The source build path will fail on trixie without either using the system waf (like pistomp-arch does for jack2) or switching to the apt package.

---

### mod-host

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Version | Commit `af11901d9d3ab02631b463853bd16d7881c4e7ca` (2025-12-27 HEAD of mod-audio/mod-host) | Branch `fix/effect-drain-midi` of `https://github.com/sastraxi/mod-host.git` |
| Repo | `https://github.com/mod-audio/mod-host` | `https://github.com/sastraxi/mod-host.git` (pistomp fork) |
| Source | Git clone + bare `make install` into `/usr/local` | PKGBUILD: `pkgbuilds/mod-host-pistomp/PKGBUILD` (installs to `/usr/bin`) |
| pkgver | N/A | 0.10.6 (PKGBUILD static placeholder; actual version from git) |

**Fork divergence flagged:** pistomp-arch uses `sastraxi/mod-host` on branch `fix/effect-drain-midi`, which contains pistomp-specific patches not present in upstream `mod-audio/mod-host`. pi-gen uses upstream at a specific commit from 2025-12-27. The branch name `fix/effect-drain-midi` suggests a MIDI drain fix that pi-gen lacks. This is a potential functional difference in MIDI behavior during effect switching.

**Binary location:** pi-gen installs to `/usr/local/bin/mod-host`; pistomp-arch installs to `/usr/bin/mod-host`. Service files reference the correct path in each system.

---

### mod-ui

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Repo | `https://github.com/TreeFallSound/mod-ui.git` (no branch specified; HEAD) | `https://github.com/sastraxi/mod-ui.git`, branch `more-fixes` |
| Install mode | `./setup.py install` (non-editable wheel) | Non-editable `uv pip install --no-deps .` into a relocatable venv |
| Python version | System Python 3.11 (bookworm) / 3.13 (trixie, broken for tornado 4.x) | Bundled Python 3.11.11 via `pistomp-python311` package at `/opt/pistomp/python311/` |
| tornado | `tornado==4.3` (global pip install) | `tornado==4.3` (in mod-ui venv only) |
| MutableMapping patch | `sed -i -e 's/collections.MutableMapping/collections.abc.MutableMapping/' /usr/local/lib/python3.11/dist-packages/tornado/httputil.py` — applied to system-wide tornado | Same sed patch applied to tornado inside the venv (`pkgbuilds/mod-ui/PKGBUILD` build() function) |
| libmod_utils.so | Built separately with `make -C utils/`, installed to system Python's dist-packages | Built in PKGBUILD build(), manually installed to `modtools/libmod_utils.so` inside the venv |
| HTML assets | `MOD_HTML_DIR=/usr/local/share/mod/html` (from `setup.py install` data_files) | `MOD_HTML_DIR=/opt/pistomp/mod-ui/html` (source tree shipped under `/opt`) |
| Port 80 binding | `authbind` wrapping the mod-ui console script | `AmbientCapabilities=CAP_NET_BIND_SERVICE` in systemd unit |
| Source venv pkg | N/A | PKGBUILD: `pkgbuilds/mod-ui/PKGBUILD` |

**Fork divergence flagged:** pi-gen uses `TreeFallSound/mod-ui` HEAD; pistomp-arch uses `sastraxi/mod-ui` branch `more-fixes`. The `more-fixes` branch may contain patches not in the TreeFallSound repo. This is the highest-priority item to reconcile because mod-ui is the largest Python component.

**Python isolation:** pistomp-arch's approach (bundled 3.11, ABI-isolated from system Python) is more robust than pi-gen's approach for trixie, where system Python becomes 3.13 and `tornado 4.x` is broken. UPGRADE-TRIXIE.md already recommends adopting the pistomp-arch pattern.

---

### amidithru / mod-amidithru

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Repo | `https://github.com/BlokasLabs/amidithru.git` (HEAD) | `https://github.com/BlokasLabs/amidithru.git` (HEAD) |
| Source | Git clone + `make install` (with `sed -i 's/CXX=g++.*/CXX=g++/' Makefile`) | PKGBUILD: `pkgbuilds/amidithru/PKGBUILD`, installs to `/usr/bin` |
| Install prefix | `/usr/local` | `/usr` |
| CXX sed fix | Yes — strips version-specific `CXX=g++-X` before building | Not needed; Arch's GCC toolchain sets `CXX` correctly |
| Service name | `mod-amidithru.service` | Not a separate service (runs as part of jack group) |

Both use HEAD of the same upstream repo with no patches. The CXX fix in pi-gen is a Debian-specific workaround.

---

### touchosc2midi

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Repo | `https://github.com/BlokasLabs/touchosc2midi.git` | `https://github.com/micahvdm/touchosc2midi.git` (different fork) |
| Install method | `pip3 install ./` (into system Python) | `uv pip install --no-deps` into dedicated `touchosc2midi` venv (Python 3.11) |
| pyliblo | Pulled in by touchosc2midi's setup.py (broken version `pyliblo 0.10.0`) | `pyliblo3` (maintained fork) installed with `Cython<3.1` before touchosc2midi |
| advertise.diff | `files/advertise.diff` prepared but commented out (`#patch -b -N -u ... -i advertise.diff`) | Not present |

**Fork divergence flagged:** pi-gen uses `BlokasLabs/touchosc2midi`; pistomp-arch uses `micahvdm/touchosc2midi`. These may have diverged.

**pyliblo breakage in pi-gen:** pi-gen installs touchosc2midi with `pip3 install ./` which pulls in `pyliblo 0.10.0` as a dep. pyliblo 0.10.0 is broken with modern liblo (signature change in `lo_blob_dataptr`) and Cython 3.x. pistomp-arch explicitly works around this with `pyliblo3` + `Cython<3.1`. The pi-gen bookworm build may be silently installing a broken pyliblo; touchosc2midi may not actually work at runtime without this fix.

---

### mod-midi-merger

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Repo | `https://github.com/micahvdm/mod-midi-merger` (micahvdm fork, not mod-audio upstream) | `https://github.com/micahvdm/mod-midi-merger.git` (same fork) |
| Source | Git clone + cmake, `sed` to disable forced `/usr` prefix, then `cmake -DCMAKE_INSTALL_PREFIX=/usr/local` | PKGBUILD: `pkgbuilds/mod-midi-merger/PKGBUILD`, uses `-DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| Install prefix | `/usr/local` | `/usr` |
| cmake policy flag | Not set (may warn) | `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` added to suppress cmake deprecation warnings |

Both use the micahvdm fork. No patches in either. pistomp-arch adds the cmake policy version flag to suppress warnings.

**Service status:** In pi-gen, `mod-midi-merger.service` and `mod-midi-merger-broadcaster.service` are installed but **not** enabled (commented out in `01-run.sh`). The service files exist in `files/services/` but `ln -sf ... /etc/systemd/system/multi-user.target.wants` is commented out. pistomp-arch status should be confirmed.

---

### mod-ttymidi

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Repo | `https://github.com/moddevices/mod-ttymidi.git` (HEAD) | `https://github.com/moddevices/mod-ttymidi.git` (HEAD) |
| Source | Git clone + `make install` | PKGBUILD: `pkgbuilds/mod-ttymidi/PKGBUILD`, installs `/usr/bin/ttymidi` |
| Install prefix | `/usr/local` | `/usr` |

Both use the same upstream repo with no patches.

**Pi 5 dtbo note:** pi-gen's `03-run.sh` downloads `midi-uart0-pi5.dtbo` from the RPi firmware repo to support ttymidi on Pi 5. pistomp-arch handles this through the device tree config rather than a separate download.

---

### sfizz

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Version | 1.2.3 | 1.2.3 |
| Repo | `https://github.com/sfztools/sfizz-ui.git#tag=1.2.3` (upstream) | `https://github.com/sfztools/sfizz-ui.git#tag=1.2.3` (upstream) |
| Build | `debpkgs/sfizz-pistomp/build.sh` → `.deb` via `dpkg-buildpackage` (prototype, not yet integrated into main build) | PKGBUILD: `pkgbuilds/sfizz-pistomp/PKGBUILD` (integrated into image build) |
| Patch | `debpkgs/sfizz-pistomp/debian/patches/add-mod-filetype.patch` | `pkgbuilds/sfizz-pistomp/add-mod-filetype.patch` |
| cmake flags | `PLUGIN_LV2=ON`, `PLUGIN_LV2_UI=OFF`, `PLUGIN_VST3=OFF`, `SFIZZ_JACK=OFF`, `SFIZZ_USE_SYSTEM_ABSEIL=OFF`, `SFIZZ_USE_SYSTEM_PUGIXML=OFF` | Identical flags |
| Parallel limit | `$(nproc)` in rules, no cap (cross-build; OOM is CI problem) | Capped at 4 jobs (`[[ $jobs -gt 4 ]] && jobs=4`) |

**Integration status differs:** pistomp-arch has sfizz fully integrated; the PKGBUILD is built during every image build and the LV2 plugin ends up on-device. pi-gen has the `.deb` infrastructure in `debpkgs/` but `build.sh` is **not called from any stage2/stage3 script** — sfizz is downloaded as part of the `lv2plugins.tar.gz` tarball instead. The debpkg is a prototype for future packaging (see `PACKAGING.md`).

**Patch is identical** between both repos — same diff, same rationale (adds `mod:fileTypes "sfz"` and `mod:fileTypes "scl"` to the LV2 .ttl for mod-ui file browser support).

---

### fluidsynth

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Version | `libfluidsynth2` from apt (bookworm ships 2.3.x) | 2.5.2 via `pkgbuilds/fluidsynth-headless/PKGBUILD` |
| Source | apt package | Custom PKGBUILD (headless: SDL disabled) |
| so version | `.so.2` (bookworm) | `.so.3` (2.5.x) |
| Shim | N/A | `pkgbuilds/libfluidsynth2-compat/PKGBUILD` — symlinks `libfluidsynth.so.2` → `libfluidsynth.so.3.X.X` for prebuilt LV2 plugins that link against `.so.2` |
| trixie change | `libfluidsynth2` removed from trixie; must switch to `libfluidsynth3` | N/A (Arch already on `.so.3`) |

**Shim divergence flagged:** pi-gen bookworm uses `.so.2` natively (no shim needed). pistomp-arch uses `.so.3` with a `.so.2` symlink shim. Trixie will also need `.so.3` and will have the same shim requirement since the LV2 plugin tarball contains prebuilt plugins linked against `.so.2`. UPGRADE-TRIXIE.md calls this out as medium severity.

**Version difference:** pistomp-arch is on FluidSynth 2.5.2; pi-gen bookworm is on whatever Debian bookworm ships (~2.3.x). This is a meaningful version gap — FluidSynth 2.4 and 2.5 have SoundFont processing improvements and bug fixes. The API is compatible (ABI of `.so.3` covers both), so this is a quality difference rather than a breaking change.

---

### browsepy

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Repo | `https://github.com/micahvdm/browsepy.git` (HEAD) | `https://github.com/micahvdm/browsepy.git` (HEAD) |
| Install method | `pip3 install ./` (into system Python, globally) | `uv pip install` into dedicated `browsepy` venv (Python 3.11) |

Same repo, different isolation. pi-gen installs browsepy globally into system Python; pistomp-arch isolates it in its own venv on the bundled Python 3.11.

---

### lg (lgpio/rgpio, Pi 5 GPIO)

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Version | N/A — uses `python3-rpi-lgpio` from apt | 0.2.2 via `pkgbuilds/lg/PKGBUILD` |
| Provides | `python3-rpi-lgpio` (apt, Raspberry Pi archive) | `liblgpio.so.1` + Python `lgpio` SWIG module at system Python site-packages |
| GCC 14 fixes | N/A (precompiled apt package) | 4 `sed` one-liners in PKGBUILD prepare() fix K&R-style function pointer typedefs and callback type mismatches that GCC 14 rejects as hard errors |
| Codebase | Joan2937 lg v0.2.2 | Joan2937 lg v0.2.2 |

**GCC 14 patches in pistomp-arch, absent in pi-gen:** The apt package `python3-rpi-lgpio` was compiled against an older GCC so these fixes are baked in. If pi-gen ever builds lg from source, these patches will be needed.

---

### lcd-splash

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Status | **MISSING** | Present — `pkgbuilds/lcd-splash/PKGBUILD` |

`lcd-splash` is a fast ILI9341 LCD boot splash for pi-Stomp (drives the hardware display before pi-stomp starts). It does not exist in pi-gen at all. No visual boot indicator on pi-gen.

---

### pistomp-recovery

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Status | **MISSING** (planned in PACKAGING.md) | Present — `pkgbuilds/pistomp-recovery/PKGBUILD` |
| Repo | N/A | `https://github.com/sastraxi/pistomp-recovery.git` (branch `main`) |

The recovery/OTA update mechanism exists only in pistomp-arch. pi-gen's PACKAGING.md describes a future equivalent but it is not implemented.

---

### jack_capture

| Attribute | pi-gen-pistomp | pistomp-arch |
|---|---|---|
| Status | **MISSING** | Present — `pkgbuilds/jack_capture/PKGBUILD` |
| Version | N/A | 0.9.73 + post-release patches |

jack_capture (records JACK output to file) only exists in pistomp-arch. See section 4 for details on the patches.

---

## 2. Python Packages

### pi-gen venvs and environments

| Environment | Location | Used by |
|---|---|---|
| System Python (global pip) | `/usr/local/lib/python3.11/dist-packages/` | mod-ui, browsepy, touchosc2midi, and any other pip installs |
| `pi-stomp` venv | `/opt/pistomp/venvs/pi-stomp` | `mod-ala-pi-stomp.service` |

### pistomp-arch venvs

| Environment | Location | Used by |
|---|---|---|
| System Python (pacman packages only) | `/usr/lib/python3.x/site-packages/` | No custom apps |
| Bundled Python 3.11 | `/opt/pistomp/python311/` | mod-ui venv, browsepy venv, touchosc2midi venv |
| `pi-stomp` venv | `/opt/pistomp/venvs/pi-stomp` | `mod-ala-pi-stomp.service` (system Python + `--system-site-packages`) |
| `mod-ui` venv | `/opt/pistomp/venvs/mod-ui` | `mod-ui.service` |
| `browsepy` venv | `/opt/pistomp/venvs/browsepy` | `browsepy.service` |
| `touchosc2midi` venv | `/opt/pistomp/venvs/touchosc2midi` | `mod-touchosc2midi.service` |
| `pistomp-recovery` venv | `/opt/pistomp/venvs/pistomp-recovery` | `pistomp-recovery.service` |

### Global pip installs (`stage2/04-python/01-run.sh`, pi-gen only)

These go into system Python in pi-gen. pistomp-arch has no equivalent global pip installs — each package lives in a specific venv.

| Package | pi-gen version | pistomp-arch venv | pistomp-arch version | Notes |
|---|---|---|---|---|
| `pyserial` | `3.0` | mod-ui venv | (latest via uv) | Pinned to 3.0 in pi-gen — 10-year-old release. 3.5 is current. |
| `pystache` | `0.5.4` | mod-ui venv | (latest via uv) | UPGRADE-TRIXIE says 0.5.4 may have issues on 3.13; latest is 0.6.8 |
| `aggdraw` | `1.3.11` | mod-ui venv | (latest via uv) | pi-gen pins to 1.3.11; current is 1.4.1 |
| `scandir` | unversioned | NONE | N/A | stdlib since Python 3.5; no-op |
| `backports.shutil-get-terminal-size` | unversioned | NONE | N/A | stdlib since Python 3.3; no-op |
| `pycryptodomex` | unversioned | mod-ui venv | `pycryptodome` (no X variant) | pi-gen installs the `pycryptodomex` namespace variant; pistomp-arch installs `pycryptodome` |
| `tornado` | `4.3` | mod-ui venv | `4.3` | Both pin to same version |
| `Pillow` | `9.4.0` | mod-ui venv | (latest via uv: `pillow`) | pi-gen pinned to 9.4.0 (2022); current is 12.x. UPGRADE-TRIXIE flags this. |
| `cython` | unversioned | touchosc2midi venv | `Cython<3.1` | pi-gen installs whatever is latest (Cython 3.x likely); pistomp-arch pins `<3.1` to avoid removing `long` builtin that pyliblo3 needs |
| `python-config` | unversioned | NONE | N/A | Build-time shim; no runtime use; UPGRADE-TRIXIE flags for removal |
| `JACK-Client` | unversioned | `pi-stomp` venv | (via uv sync from pyproject.toml) | Both need this |
| `flask` | unversioned | NONE (browsepy brings its own) | N/A | Only in pi-gen global; not needed globally |
| `unicategories` | unversioned | NONE | N/A | Only in pi-gen global |
| `pep8` | unversioned | NONE | N/A | Deprecated alias for pycodestyle; dev tool only; UPGRADE-TRIXIE flags for removal |
| `flake8` | unversioned | NONE | N/A | Dev tool only; UPGRADE-TRIXIE flags for removal |
| `coverage` | unversioned | NONE | N/A | Dev tool only; UPGRADE-TRIXIE flags for removal |
| `pyaml` | unversioned | `pi-stomp` venv | (via uv sync) | |
| `sphinx` | unversioned | NONE | N/A | Dev/doc tool; UPGRADE-TRIXIE flags for removal |
| `netifaces` | `0.10.5` | touchosc2midi venv | `netifaces` (unversioned, likely netifaces2) | 0.10.5 fails to build on Python 3.12+; UPGRADE-TRIXIE requires `netifaces2` |
| `mido` | `1.1.24` | touchosc2midi venv | `mido` (unversioned) | pi-gen pins to 2017-era version; current is 1.3.3 |
| `docopt` | `0.6.2` | touchosc2midi venv | `docopt` (unversioned) | |

### touchosc2midi venv (pistomp-arch only, no direct equivalent in pi-gen)

pistomp-arch `scripts/05-python.sh` installs these into the `touchosc2midi` venv:

| Package | pistomp-arch version | pi-gen equivalent |
|---|---|---|
| `pyliblo3` | Latest (with `Cython<3.1` and `--no-build-isolation`) | `pyliblo 0.10.0` (broken, pulled by setup.py) |
| `python-rtmidi` | Latest | Part of touchosc2midi install |
| `mido` | Latest | `mido==1.1.24` (global) |
| `docopt` | Latest | `docopt==0.6.2` (global) |
| `netifaces` | Latest | `netifaces==0.10.5` (global) |
| `zeroconf` | Latest | (system package `python3-zeroconf` in apt) |

### pi-stomp venv

Both systems create the pi-stomp venv with `--system-site-packages`, pointing to the system Python. The venv is populated by `uv sync --frozen --no-dev --extra hardware` from `pi-stomp/pyproject.toml`. The exact packages depend on that lock file.

Key system packages that must be present before `uv sync`:
- `python-lilv` / `python3-lilv` — provides `import lilv`
- GPIO: `python3-lgpio` (pi-gen) vs `lgpio` from the `lg` PKGBUILD (pistomp-arch)

---

## 3. System/APT/Pacman Packages

### Audio

| Package | pi-gen (bookworm) | pistomp-arch | Notes |
|---|---|---|---|
| ALSA utils | `alsa-utils` (via apt, in 00-packages) | `alsa-utils alsa-lib` | Both |
| Sample rate | `libsamplerate0-dev` (for builds) | `libsamplerate` | Both; pi-gen has dev header for source builds |
| Sndfile | `libsndfile1-dev` (for builds) | `libsndfile` | Both |
| FFTW | `libfftw3-dev` | `fftw` | Both |
| LV2 SDK | `lv2-dev` | `lv2` | Both |
| liblo (OSC) | `liblo-dev python3-liblo` | `liblo` | Both; pi-gen has python3-liblo for system Python |
| libfluidsynth | `libfluidsynth-dev libfluidsynth2` | `fluidsynth-headless` (PKGBUILD) | Version difference: bookworm .so.2 vs arch .so.3 |
| serd/sord/sratom | `libserd-dev libsord-dev libsratom-dev` (from `00-packages-nr`) | `serd sord sratom` | Both |
| LRDF | `liblrdf0-dev` | **MISSING** | Low risk: liblrdf is an old RDF library; may be needed by mod-host or older LV2 plugins |
| Zita convolver | `libzita-convolver-dev` | **MISSING** | May be needed by LV2 plugins in the tarball |
| Zita resampler | `libzita-resampler-dev` | **MISSING** | Same |
| LADSPA SDK | `ladspa-sdk` | **MISSING** | Low risk if no LADSPA plugins are in the tarball |
| Boost | `libboost-dev` | **MISSING** | Required by jack2 waf build; pistomp-arch likely gets it via a transitive dependency |
| Eigen3 | `libeigen3-dev` | **MISSING** | Math library; possibly required by mod-host |
| RT IRQ | **MISSING** | `rtirq` | pistomp-arch installs rtirq to set RT priorities on IRQ threads |
| ffmpeg | **MISSING** | `ffmpeg` | pistomp-arch installs ffmpeg |

### GPIO/Hardware

| Package | pi-gen (bookworm) | pistomp-arch | Notes |
|---|---|---|---|
| gpiod | `gpiod python3-libgpiod` | `libgpiod` | Both; pi-gen has Python bindings via apt, pistomp-arch does not have python3-libgpiod (uses lgpio instead) |
| gpiozero | `python3-gpiozero` | **MISSING** (added via pi-stomp uv sync) | pi-gen installs system-wide; pistomp-arch gets it via venv |
| pigpio | `pigpio python3-pigpio raspi-gpio python3-rpi.gpio` | **MISSING** | pigpio and raspi-gpio removed from trixie. pistomp-arch correctly omits them |
| RPi.GPIO | `python3-rpi.gpio` → replaced with `python3-rpi-lgpio` | **MISSING** | pistomp-arch uses its own `lg` PKGBUILD |
| lgpio | Provided by `python3-rpi-lgpio` (RPi archive) | `lg` PKGBUILD (joan2937/lg 0.2.2) | Different implementations of the same concept |
| SPI | `python3-spidev` | **MISSING** | Required for pi-stomp hardware SPI (LCD); may be in pi-stomp's venv deps |
| SMBus | `python3-smbus2` | **MISSING** | Required for I2C; may be in pi-stomp's venv deps |
| I2C utils | `i2c-tools` (not in 00-packages but likely in system) | `i2c-tools` | pistomp-arch has it explicitly |

### Networking

| Package | pi-gen | pistomp-arch | Notes |
|---|---|---|---|
| NetworkManager | `network-manager` | `networkmanager` | Both |
| wpa_supplicant | `wpasupplicant wireless-tools` | Not installed (NM handles directly) | pistomp-arch uses NM's built-in WPA supplicant |
| WiFi firmware | `firmware-atheros firmware-brcm80211 firmware-libertas firmware-misc-nonfree firmware-realtek` | Provided by `linux-rpi` kernel package + RPi firmware | Different mechanism, same result |
| avahi | `avahi-daemon` | `avahi nss-mdns` | pistomp-arch also sets nsswitch.conf to use mdns_minimal |
| dnsmasq | `dnsmasq` | `dnsmasq` | Both |
| hostapd | Not explicit (may be in pi-stomp setup) | `hostapd` | pistomp-arch installs it explicitly for hotspot |
| net-tools | `net-tools` | **MISSING** | Low risk; mostly used for `ifconfig` which iproute2 replaces |
| ethtool | `ethtool` | **MISSING** | Low risk |

### Python C Extensions (system-level)

| Package | pi-gen | pistomp-arch | Notes |
|---|---|---|---|
| python3-lilv | Installed from source build | `python-lilv` (pacman) | Both have it |
| python3-lgpio | `python3-rpi-lgpio` (RPi archive) | `lgpio` module from `lg` PKGBUILD | Functionally equivalent |
| python3-smbus | `python3-smbus2` | **MISSING** at system level (in venv) | |
| python3-spidev | `python3-spidev` | **MISSING** at system level | |
| python3-gpiozero | `python3-gpiozero` | **MISSING** at system level | |

### Build Tools

| Package | pi-gen | pistomp-arch | Notes |
|---|---|---|---|
| build-essential / base-devel | `build-essential` | `base-devel` | Both |
| cmake | `cmake` (in 00-packages) | `cmake` (installed by PKGBUILDs) | Both |
| swig | `swig` (in 00-packages) | `swig` (installed by PKGBUILDs) | Both |
| meson | `meson` (in `00-packages-nr`) | Not in pacman install but available | |
| ninja-build | `ninja-build` (in `00-packages-nr`) | Part of `base-devel` or installed by meson | |
| git | `git` (in 00-packages) | `git` | Both |
| pkg-config | `pkg-config` (in 00-packages) | Part of `base-devel` | Both |
| uv | Installed via curl from astral.sh | Installed via curl from astral.sh | Both use the same installer |

### Misc / General System

| Package | pi-gen | pistomp-arch | Notes |
|---|---|---|---|
| Avahi | `avahi-daemon` | `avahi nss-mdns` | |
| ca-certificates | `ca-certificates curl` | Included in base | |
| fake-hwclock | `fake-hwclock` | **MISSING** | pi-gen uses this for systems without RTC; relevant for Pi 3/4 without hardware clock |
| authbind | `authbind` | **MISSING** | pi-gen uses authbind for port 80; pistomp-arch uses `AmbientCapabilities=CAP_NET_BIND_SERVICE` |
| nfs-common | `nfs-common` | **MISSING** | NFS client support |
| usbutils | `usbutils` | **MISSING** | Low risk |
| dosfstools | `dosfstools` | `dosfstools` | Both (needed for FAT32 boot partition) |
| parted | `parted` | `parted` | Both |
| rsync | `rsync` | `rsync` | Both |
| htop | `htop` | `htop` | Both |
| unzip/7zip | `unzip zip p7zip-full` | `7zip bzip2 unzip` | Both |
| raspberrypi-utils | `raspberrypi-sys-mods raspi-utils rpi-eeprom` | `raspberrypi-utils` | Similar coverage |
| cloud-guest-utils | **MISSING** | `cloud-guest-utils` | pistomp-arch uses `growpart` from this package for first-boot partition resize |
| sdl2 / freetype2 | **MISSING** | `sdl2 freetype2` | Required by pistomp-recovery's pygame dependency |
| ttf-dejavu | **MISSING** | `ttf-dejavu` | Font for lcd-splash and recovery UI |
| rcconf | `rcconf` (removed in trixie) | **MISSING** | Pi-gen legacy; not needed |
| policykit-1 | `policykit-1` (renamed to `polkit` in trixie) | Not needed (no GUI) | |
| authbind | `authbind` | **MISSING** | Not needed in pistomp-arch (uses CAP_NET_BIND_SERVICE) |
| lockfile-progs | `lockfile-progs` | **MISSING** | Used by pi-gen firstboot? |
| udisks2 | `udisks2` | **MISSING** | USB automount; pi-gen uses usbmount.deb (broken on trixie) |
| zram | **MISSING** | Part of kernel + service | pistomp-arch enables zram before JACK |

---

## 4. Patches: What We Have vs. What's Missing

### pistomp-arch patches

| Patch file | What it patches | Why | Equivalent in pi-gen? |
|---|---|---|---|
| `pkgbuilds/jack2-pistomp/pi-controller-reset.patch` | jack2 `JackAudioAdapterInterface.cpp` | Clears PI controller integrator windup on ringbuffer reset, preventing monotonically increasing failure rate on netadapter connections | **NO** — critical missing patch in pi-gen |
| `pkgbuilds/jack2-pistomp/jack2-1.9.22-db-5.3.patch` | jack2 `wscript` | Uses `db5.3/db.h` header path (Arch BerkeleyDB naming) | Not applicable to Debian (different header path convention) |
| `pkgbuilds/sfizz-pistomp/add-mod-filetype.patch` | `sfizz-ui/plugins/lv2/sfizz.ttl.in` | Adds `mod:fileTypes "sfz"` and `mod:fileTypes "scl"` annotations for mod-ui file browser | YES — identical patch at `debpkgs/sfizz-pistomp/debian/patches/add-mod-filetype.patch` |
| `pkgbuilds/jack_capture/jack_capture-post-release-fixes.patch` | `jack_capture.c`, `vringbuffer.c`, `vringbuffer.h` | 29-commit bundle of post-0.9.73-tag upstream fixes: enum type safety, semaphore abstraction, `--jack-name` flag, `--mp3-samplerate` flag, auto file format from extension | **NO** — jack_capture not in pi-gen |
| `pkgbuilds/jack_capture/jack_capture-file-rotation.patch` | `jack_capture.c` | Fixes file rotation to prevent overwriting existing files (GitHub issue #56); adds dedicated filename generation functions | **NO** — jack_capture not in pi-gen |
| `pkgbuilds/lg/PKGBUILD` (inline sed) | `lgpio.h`, `lgGpio.h`, `lgGpio.c` | GCC 14 K&R-style function pointer typedef fixes; prevents hard "too many arguments" compile errors | Not applicable (pi-gen uses prebuilt apt package) |
| mod-ui tornado MutableMapping patch (inline in PKGBUILD) | `tornado/httputil.py` | `collections.MutableMapping` → `collections.abc.MutableMapping` for Python 3.10+ | YES — same sed in `stage2/05-pistomp/02-run.sh` line 64, but pi-gen applies it to the wrong path on trixie |

### pi-gen-only patches

| Patch file | What it patches | Why | Equivalent in pistomp-arch? |
|---|---|---|---|
| `stage2/05-pistomp/files/advertise.diff` | `touchosc2midi/advertise.py` | Changes `address=socket.inet_aton(ip)` → `addresses=[socket.inet_aton(ip)]` for newer zeroconf API | **Commented out** in `03-run.sh` line 17 — not applied |
| `stage2/05-pistomp/files/NetworkManager.conf.diff` | `/etc/NetworkManager/NetworkManager.conf` | Adds `dns=dnsmasq` | YES — pistomp-arch sets this in `scripts/02-system.sh` directly in the NetworkManager.conf template |
| `stage1/01-sys-tweaks/00-patches/01-bashrc.diff` | `/etc/bash.bashrc` | Adds some prompt/completion tweaks | Not applicable (different shell init) |
| `stage2/01-sys-tweaks/00-patches/` (5 patches) | Various system files (useradd, swap, inputrc, path, resize-init) | Standard pi-gen system tweaks | Not applicable (Arch has different defaults) |

---

## 5. Duplicates / Redundancy

### Within pi-gen-pistomp

1. **`python3-rpi-lgpio` installed twice:** In `stage2/01-sys-tweaks/00-packages` (implicit via the rpi.gpio → lgpio swap line), then again in `stage2/04-python/01-run.sh` lines 33–37 (`sudo apt-get -y install python3-rpi-lgpio` and `sudo apt install python3-rpi-lgpio`). The second block runs `apt install` twice in a row. UPGRADE-TRIXIE flags this.

2. **`scandir` pip installed, already stdlib:** `pip3 install scandir` in `stage2/04-python/01-run.sh`. `os.scandir` is in Python's stdlib since 3.5. The PyPI package is a no-op on 3.x. Installing it wastes time and potentially confuses package management.

3. **`backports.shutil-get-terminal-size` pip installed, already stdlib:** `shutil.get_terminal_size` is in stdlib since Python 3.3. Same situation as scandir.

4. **jack2 source build vs. jack-dummy package:** The `jack-dummy` equivs package in `stage2/00-dummy-packages/` satisfies `libjack-jackd2-0`, `libjack-jackd2-dev`, `jackd2` so that the real jack2 can be built from source. This is a build-time workaround; if the trixie plan to switch to apt `jackd2` is adopted, the dummy package should be removed to avoid conflict.

5. **`pip3 install pep8` then `pip3 install flake8`:** `pep8` is a deprecated alias for `pycodestyle`. `flake8` depends on `pycodestyle` anyway. Both are dev tools; neither belongs in a production image.

### Within pistomp-arch

1. **`uv` installed twice:** Installed via `curl` in `04-native-pkgs.sh`, but `uv` is also listed as a `makedepend` in multiple PKGBUILDs (`mod-ui`, `pi-stomp`, `pistomp-recovery`, `pistomp-python311`). The PKGBUILDs expect `uv` to be available via pacman/system PATH, but the image build installs it to `/opt/pistomp/bin/uv`. This works because `04-native-pkgs.sh` runs before the PKGBUILDs and the PKGBUILD `makedepends=('uv')` is satisfied by `pacman -S uv` (which Arch has in the community/extra repos). Verify this is not pulling a second uv from the system package.

2. **`libfluidsynth2-compat` is a shim-only package:** It has no content besides a symlink. It is listed in `pkgver=2.3.4` which is the version of FluidSynth it pretends to be `.so.2` for, but it depends on `fluidsynth-headless` (2.5.2). The version field is misleading but this is a minor metadata issue, not a functional one.

---

## 6. Stability Risk Summary

| Item | Risk | Why |
|---|---|---|
| **pi-gen missing jack2 `pi-controller-reset.patch`** | **High** | Without this, the PI controller integrator winds up unboundedly across ringbuffer resets on netadapter connections. Failure rate ramps monotonically from jackd start; only restarting jackd restores clean operation. Confirmed root-caused and fixed in pistomp-arch. |
| **pi-gen `tornado==4.3` on trixie (Python 3.13)** | **High** | tornado 4.x is incompatible with Python 3.13 (`asyncio.get_event_loop()`, `@gen.engine`, `collections.MutableMapping`). mod-ui will not start. Requires running mod-ui in a Python 3.11 venv (the pistomp-arch model). Already documented in UPGRADE-TRIXIE.md. |
| **pi-gen `usbmount.deb` on trixie** | **High** | `usbmount` was built for bullseye. `dpkg -i` will fail on trixie due to broken dependencies; the build will abort at that step. UPGRADE-TRIXIE.md calls this out. |
| **pi-gen `pigpio` removed in trixie** | **High** | `pigpio` and `python3-pigpio` are not in Debian 13 or the RPi trixie archive. If pi-stomp code imports `pigpio`, it will crash at startup. Must be replaced with `python3-lgpio` / the lg PKGBUILD equivalent. |
| **pi-gen `lilv 0.24.12` waf build on trixie** | **High** | The bundled waf in lilv 0.24.12 uses the `imp` module removed in Python 3.12. The source build will fail completely unless waf is replaced or lilv switches to the apt package (trixie: `liblilv-dev 0.24.26-1`). |
| **pi-gen `netifaces==0.10.5` on trixie** | **High** | netifaces 0.10.5 fails to build from source on Python 3.12+ (removed C APIs). Hard build failure. Replace with `netifaces2`. |
| **pi-gen `libfluidsynth2` → `libfluidsynth3` on trixie** | **Medium** | `libfluidsynth2` removed from Debian 13. Prebuilt LV2 plugins in `lv2plugins.tar.gz` link against `.so.2`; they will fail to load unless a `.so.2 → .so.3` shim symlink is created (the pistomp-arch `libfluidsynth2-compat` approach). |
| **pi-gen `pyliblo 0.10.0` (via touchosc2midi install)** | **Medium** | `pyliblo 0.10.0` is incompatible with modern liblo and Cython 3.x. touchosc2midi may install silently but fail at runtime when initializing its OSC transport. pistomp-arch fixes this with `pyliblo3` + `Cython<3.1`. |
| **pi-gen mod-ui repo divergence from pistomp-arch** | **Medium** | pi-gen uses `TreeFallSound/mod-ui` HEAD; pistomp-arch uses `sastraxi/mod-ui` branch `more-fixes`. Any bug fixes on the `more-fixes` branch are not present in pi-gen. Without knowing the exact diff, the risk is unknown but possibly Medium. |
| **pi-gen mod-host repo divergence from pistomp-arch** | **Medium** | pi-gen uses `mod-audio/mod-host@af11901` (upstream); pistomp-arch uses `sastraxi/mod-host` branch `fix/effect-drain-midi`. MIDI behavior during effect switching may differ. |
| **pi-gen `lilv 0.24.12` vs. pistomp-arch `0.24.26`** | **Medium** | 4-point version gap. API is backward compatible, but new features/fixes (e.g. LV2 State, LV2 Atom improvements) in 0.24.26 may be relied upon by newer LV2 plugins in the shared plugin tarball. |
| **pi-gen `Pillow==9.4.0` (2022)** | **Low** | Pinned to a 4-year-old release. Possible silent incompatibilities with newer Python, but Pillow 9.4.0 explicitly supports Python 3.11. Not broken on bookworm; may fail on trixie (Python 3.13 requires Pillow 10+). |
| **pi-gen `pystache==0.5.4`** | **Low** | Possible silent runtime failures on Python 3.13. Unpin and take 0.6.8. No known breakage on 3.11. |
| **pi-gen `mido==1.1.24`** | **Low** | 2017-era release. API compatible, but may miss bug fixes relevant to MIDI handling. |
| **pi-gen `pyserial==3.0`** | **Low** | 2016-era release. Functionally stable; unlikely to cause issues. |
| **pi-gen missing `rtirq`** | **Low** | IRQ threads run at stock priority without rtirq. On a non-RT kernel this may not matter much, but on the RT kernel it means ALSA IRQs are not boosted to audio-class priority. pistomp-arch installs rtirq and enables the service. |
| **pi-gen `advertise.diff` commented out** | **Low** | The zeroconf API change (`address=` → `addresses=[]`) affects touchosc2midi's mDNS advertisement. The diff is staged but not applied. touchosc2midi may fail to advertise over mDNS. Risk is low because this is an optional feature (not a hard startup failure). |
| **pistomp-arch missing `fake-hwclock`** | **Low** | Systems without a hardware RTC will lose the time after reboot; NTP must reconnect to restore it. On headless audio appliances this is typically acceptable. |
