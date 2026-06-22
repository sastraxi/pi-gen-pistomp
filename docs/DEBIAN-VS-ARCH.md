# Debian package build vs. pistomp-arch (Arch Linux) — known differences

This document records intentional and structural differences between the `.deb`
packages built here and the equivalent Arch `PKGBUILD`s in `pistomp-arch`.
It is a living reference: add entries when a difference is confirmed, update
them when behaviour converges.

---

## Build architecture

| | Debian (pi-gen-pistomp) | Arch (pistomp-arch) |
|---|---|---|
| Base system | Raspberry Pi OS Trixie (debootstrap via pi-gen) | Arch Linux ARM (pacstrap) |
| Build flow | pi-gen stages 0–2 inside Docker | 10 sequential `run_in_chroot` scripts |
| Kernel compilation | Cross-compile x86_64 → arm64 | Native aarch64 inside chroot |
| Package format | `.deb` (dpkg/apt) | `.pkg.tar.zst` (pacman) |
| Custom packages | 17 `.deb` packages | 18 `.pkg.tar.zst` packages |
| Final compression | xz (configurable: zip/gz/xz/none) | zstd -T0 -3 |

The two-phase approach is the same in both repos: build the RT kernel once
(cached), then build the OS image consuming it.

---

## Package coverage

| Package | Debian | Arch | Notes |
|---|---|---|---|
| jack2-pistomp | ✓ | ✓ | See below |
| mod-host-pistomp | ✓ | ✓ | |
| mod-ui | ✓ | ✓ | See below |
| pi-stomp | ✓ | ✓ | |
| pistomp-recovery | ✓ | ✓ | |
| lg (lgpio) | ✓ | ✓ | See below |
| lcd-splash | ✓ | ✓ | |
| hylia | ✓ | ✓ | |
| sfizz-pistomp | ✓ | ✓ | |
| fluidsynth-headless | ✓ | ✓ | |
| libfluidsynth2-compat | ✓ | ✓ | |
| amidithru | ✓ | ✓ | |
| mod-midi-merger | ✓ | ✓ | |
| mod-ttymidi | ✓ | ✓ | |
| jack-capture | ✓ | ✓ | See below |
| browsepy | ✓ deb | venv in 05-python.sh | Debian packages it; Arch builds a lightweight venv |
| touchosc2midi | ✓ deb | venv in 05-python.sh | Same |
| jackbridge | ✓ deb | — | Not found in Arch; may be omitted |
| pistomp-python311 | — | ✓ | Arch ships a standalone Python 3.11 package; Debian embeds it in the mod-ui venv |

---

## jack2-pistomp

### waf invocation

Both builds apply the same two patches (`jack2-1.9.22-db-5.3.patch`,
`pi-controller-reset.patch`) and solve the same problem: the bundled waflib
uses the `imp` module removed in Python 3.12.

| | Arch | Debian |
|---|---|---|
| waflib source | System `waf` (bundled waflib deleted in `prepare()`) | Bundled `./waf` + `waflib-imp-to-types.patch` |
| Invocation | `waf configure && waf build` | `./waf configure && ./waf build` |
| PYTHONPATH | `export PYTHONPATH="${PWD}:${PYTHONPATH:-}"` (both build and install) | Not set — `./waf` finds its own tools |

The PYTHONPATH export in Arch is a consequence of using system waf (which
needs to locate jack2's waf tool modules via the Python path). With the
bundled `./waf`, this is handled internally and PYTHONPATH is not needed.

### Debian-only patches

- `systemd-pkgconfig.patch` — fixes systemd.pc detection on Debian Trixie
- `systemd-unit-dir.patch` — provides a fallback unit dir when pkg-config returns nothing

These are not needed on Arch because Arch's systemd packaging exposes
pkg-config differently.

---

## jack-capture

| | Arch | Debian |
|---|---|---|
| Base | `v0.9.73` tag | Post-0.9.73 master commit pinned via `JACK_CAPTURE_REF` |
| Post-release fixes | Applied via `jack_capture-post-release-fixes.patch` (29 commits) | Already included in the pinned commit — no patch needed |

---

## mod-ui — Python 3.11 isolation

| | Arch | Debian |
|---|---|---|
| Python 3.11 source | Separate `pistomp-python311` package at `/opt/pistomp/python311/` | `uv python install 3.11` into uv's build cache |
| Venv creation | `uv venv --python /opt/pistomp/python311/bin/python3.11 --relocatable` | `uv python find 3.11 \| xargs python -m venv --copies` |
| Runtime dependency | `pistomp-python311` package must be installed | Python 3.11 binary is copied into the venv; no external dep |

The Debian venv is fully self-contained: the Python 3.11 binary lives at
`/opt/pistomp/venvs/mod-ui/bin/python3.11`. The Arch approach is more
modular (Python version is a separate versioned package), but both achieve
the same isolation from system Python 3.13.

---

## lg (lgpio) — Python module installation

Arch uses `setup.py install --root=...` (discovers site-packages at package
time). The Debian build installs the two files manually to avoid
`dh_usrlocal` rejecting files under `/usr/local/` and to sidestep the
`setup.py install` deprecation warning:

```
/usr/lib/python3/dist-packages/lgpio.py
/usr/lib/python3/dist-packages/_lgpio.so
```

---

## pi-stomp / pistomp-recovery — venv strategy

Both packages use `--system-site-packages` against `/usr/bin/python3` (system
Python 3.13). Because `/usr/bin/python3` exists on the target device,
`--copies` is not needed — the venv symlink is valid at runtime.

Arch uses `--relocatable`; Debian uses plain `uv venv` (relocation is not
required when the interpreter path is stable across build and target).

`uv sync` is called with `--no-editable` in both repos so the project wheel
lands in `site-packages` rather than as an editable `.pth` pointing to the
build tree.

---

## Python environment overview

| Component | Debian | Arch |
|---|---|---|
| System Python | 3.13 (`/usr/bin/python3`) | 3.13 (`/usr/bin/python`) |
| mod-ui | Python 3.11 copied into venv | Python 3.11 via `pistomp-python311` package |
| pi-stomp | System Python 3.13 venv + `--system-site-packages` | Same |
| pistomp-recovery | System Python 3.13 venv + `--system-site-packages` | Same |
| browsepy | `.deb` with venv | Venv created in 05-python.sh |
| touchosc2midi | `.deb` with venv | Venv created in 05-python.sh |
| System-wide pip installs | Yes — stage2/04-python installs pyliblo3, netifaces2, JACK-Client, etc. via pip3 (EXTERNALLY-MANAGED removed) | No — all packages isolated to venvs |

---

## uv availability

`uv` is not a Debian package and cannot be declared in `Build-Depends` or
`Depends`. It is installed into the Docker build image via
`pip3 install uv --break-system-packages` (Dockerfile layer 4).

No installed package declares a runtime dependency on `uv` — all venvs are
pre-built and self-contained.

In Arch, `uv` is installed inside the chroot during 04-native-pkgs.sh via
the official install script, and is available to all PKGBUILDs.

---

## systemd service enablement

Both repos use manual `ln -sf` symlinks into `wants/` directories rather than
`systemctl enable` or `deb-systemd-helper`. Debian's deb rules override
`dh_installsystemd` to prevent it from running.

### Service list differences

| Service | Debian | Arch |
|---|---|---|
| rtirq | ✓ | — |
| mod-midi-merger-broadcaster | — | ✓ |
| wifi-check / wifi-hotspot | wifi-check.service | wifi-hotspot.service |

### mod-ala-pi-stomp.service restart policy

| | Debian | Arch |
|---|---|---|
| `Restart=` | `always` | `on-failure` |
| `RestartSec=` | 2 s | 5 s |
| `LimitRTPRIO=` | 64 | 70 |
| Explicit `Requires=` | mod-ui only | jack + mod-host + mod-ui |

---

## Networking

Both match on: NM keyfile plugin, dnsmasq, wifi power-save off, MAC
randomization off, wired DHCP → link-local fallback, multihome policy-routing
dispatcher.

One confirmed difference: wired NM profile uses **`eth0`** here and **`end0`**
in Arch. Modern kernels with predictable interface naming use `end0`; older or
RPi-specific udev rules may use `eth0`. Check which name the target kernel
exposes before changing either.

---

## Kernel

| | Debian | Arch |
|---|---|---|
| Source | Raspberry Pi Linux (pinned commit in config.sh) | Arch ARM linux-rpi PKGBUILD base (pinned commit) |
| diffconfig | ~99 lines (RT + size optimisations, disables XFS/BTRFS/GPU debug) | ~400 lines (Arch ARM baseline + RT additions) |
| Build method | Cross-compile x86_64 → arm64 (`bindeb-pkg`) | Native aarch64 (`makepkg`) |
| Output | `.deb` files in `stage2/05-pistomp/files/sys/` | `.pkg.tar.*` files in `cache/` |
| Arch extra patches | — | `disable-heavy-features.patch`, `0001-Make-proc-cpuinfo-consistent-on-arm64-and-arm.patch` |

---

## Cleanup

| | Debian | Arch |
|---|---|---|
| Build toolchain | Kept (part of base OS) | Removed (`base-devel`, gcc, kernel headers) |
| Kernel module pruning | Minimal | Explicit — removes GPU/network/staging drivers |
| Firmware pruning | Minimal | Keeps only brcm/cypress (RPi WiFi/BT) |
| Python/uv cache | Basic | Removes uv download cache explicitly |
| SBOM | syft generates SBOM on export | Not generated |

---

## Possible gaps (to investigate)

These are things Arch does that have no confirmed equivalent here. They may
already be handled or may be genuinely missing — not yet verified.

- **jackbridge** — present as a `.deb` here but not found in pistomp-arch;
  unclear if it is needed at runtime.
- **Audio limits** — Debian installs `/etc/security/limits.d/99-audio.conf`
  and a udev rule for CPU DMA latency (`99-cpu-dma-latency.rules`). Arch
  relies on `LimitRTPRIO=70` in the service unit. Verify whether the limits
  file is actually required.
- **eth0 vs end0** — see Networking section above.
- **mod-ala-pi-stomp Requires** — Arch explicitly requires jack and mod-host;
  Debian relies on transitive ordering. Check whether a boot-time race is
  possible.
