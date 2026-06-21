# pi-gen-pistomp vs. pistomp-arch: full comparison

This document compares the current state of `pi-gen-pistomp` (Debian/RPi OS based, targeting `bookworm` as of writing) with `pistomp-arch` (Arch Linux ARM based). The goal is to honestly assess where each stands and inform decisions about which to invest in.

> RPi OS trixie (Debian 13, Python 3.13) shipped October 2025. The current pi-gen-pistomp is still on bookworm. See `UPGRADE-TRIXIE.md` for what it takes to get there. The trixie column below reflects where pi-gen-pistomp would be *after* that upgrade.

---

## 1. Dependency hell / segfaults

**pi-gen (bookworm):** Native C components (`jack2`, `lilv`, `mod-host`, `sfizz`, etc.) are built by bare `make install` into `/usr/local/` — dpkg tracks nothing. System packages that conflict are suppressed with an `equivs` dummy `.deb` (`jack-dummy`). The Debian bookworm packages for sfizz (1.1.1, 2021) and lilv (0.24.12) are outdated or broken; we build both from source. `sfizz` 1.1.1 segfaults on our hardware. `lilv 0.24.12`'s bundled waf uses the `imp` module, removed in Python 3.12.

**pi-gen (trixie, after upgrade):** `jackd2 1.9.22` and `liblilv 0.24.26` are both available in trixie apt at exactly the versions we want — the source builds for those two can be dropped entirely. `sfizz` is still broken in Debian apt and still requires a custom build or the `debpkgs/` fork approach from `PACKAGING.md`.

**pistomp-arch:** Every C component is a `PKGBUILD` with an explicit `pkgver=` pin and `provides=`/`conflicts=` so pacman enforces the override cleanly. `sfizz-pistomp` 1.2.3 with correct CMake flags is a first-class pacman package.

**Verdict:** pistomp-arch wins now. trixie closes the jack2 and lilv gap, but sfizz and anything else not in Debian still require the `debpkgs/` infrastructure described in `PACKAGING.md`. That infrastructure doesn't exist yet.

---

## 2. Package tracking and upgrade path

**pi-gen:** `dpkg -l` doesn't know jack2, sfizz, lilv, mod-host, or amidithru exist. No clean upgrade or removal. Devices in the field can't pull a fixed build of anything without reflashing.

**pistomp-arch:** All components are pacman packages. `pacman -Syu` upgrades everything. The custom `[pistomp]` pacman repo on GitHub Releases publishes pre-built packages. pistomp-recovery uses pacman's package cache for rollback.

**Verdict:** pistomp-arch wins. The trixie upgrade doesn't change this — it requires the `debpkgs/` + apt repo work in `PACKAGING.md` to reach parity.

---

## 3. Python venv story

**pi-gen (bookworm):** `04-python/01-run.sh` removes `EXTERNALLY-MANAGED` and `pip3 install`s a laundry list to system Python 3.11 — pinned versions mixed with unpinned, including `tornado==4.3` (2015). `stage3` then creates a uv venv with `--system-site-packages` that inherits this global pip mess. Two entangled Python environments.

**pi-gen (trixie):** `netifaces==0.10.5` fails to compile on Python 3.13, and `lilv`'s waf build fails due to the removed `imp` module — but these are straightforward fixes. The tornado issue is **not a blocker**: mod-ui runs in its own uv-managed Python 3.11 venv (same as pistomp-arch), keeping tornado 4.x on Python 3.11 where it works. The global pip install list still needs cleanup (drop dead packages, fix version pins), but no porting work is required.

**Python version:** bookworm ships 3.11.2; trixie ships 3.13.5 (as of June 2026). This is a meaningful jump — newer stdlib, faster interpreter — but it requires the mod-ui tornado porting work to land first.

**pistomp-arch:** pyenv pins Python 3.11.11. Each app has its own isolated venv: pi-stomp uses system Python with `--system-site-packages` (needs pacman C extensions); mod-ui, browsepy, touchosc2midi use pyenv Python 3.11. All managed by uv. No global pip mess. The pyenv pin means pistomp-arch is currently *behind* trixie on Python version; adopting 3.13 there also requires the mod-ui tornado work.

**Verdict:** pistomp-arch wins on isolation and reproducibility. Both repos face the same tornado/mod-ui porting work to get to Python 3.13.

---

## 4. Boot time

**pi-gen firstboot sequence:**
1. RPi OS `resize2fs_once` (SysV init script — runs early, blocks until done)
2. `firstboot.service`: copies `config_pistomp.txt` → `config.txt` to activate RT kernel overlay, copies ALSA state, detects Pi model, runs pi5 EEPROM update → **reboots**
3. Second boot with RT kernel config: all services cold-start (jack, mod-host, mod-ui, browsepy, amidithru, pi-stomp)
4. `mod-ui` cold-starts Tornado, waits for JACK and mod-host — no readiness probes, so dependents start before their dependencies are ready, causing crash-restart cycles

**Where the time goes:** The extra reboot (caused by firstboot switching `config.txt` to enable the RT overlay) is avoidable — the RT overlay could be baked in at image build time. The missing readiness probes before mod-ui cause systemd restart loops that add minutes to the usable-state time. The `mod-ui` service points at `MOD_HTML_DIR=/usr/local/share/mod/html`, which pip's editable install never populates — this causes an immediate crash on startup, compounding the restart loop.

**pistomp-arch:**
1. `firstboot.service`: applies `pistomp.conf` (WiFi, hostname, password, timezone, SSH key), `growpart`/`resize2fs`, writes JACK settings, Pi model detection → **reboots**
2. Second boot: zram → jack → mod-host → mod-ui/browsepy → mod-ala-pi-stomp, each waiting for the previous (`wait-for-mod-host.sh` before mod-ui). LCD splash narrates progress.

**Verdict:** pistomp-arch wins, significantly. The extra reboot in pi-gen is the same count, but the crash-restart loops from missing readiness probes add real minutes. The LCD splash makes the subjective experience radically different.

---

## 5. LCD during boot (white/blank screen)

**pi-gen:** No LCD splash. No `pistomp-lcd-splash`, no boot splash, nothing. The display is dark or at hardware default until pi-stomp fully initializes. During both boots, during the restart loop period, during mod-ui initialization — uninformative blank screen.

**pistomp-arch:** `pistomp-lcd-splash.service` is a sysinit unit — starts at the very beginning of the boot sequence, before most other services. Displays the pi-Stomp logo immediately. Service startup narrates progress via `ExecStartPre=/usr/bin/lcd-splash`. Shutdown and reboot also show messages (`lcd-reboot.service`, `lcd-shutdown.service`, `lcd-safe-poweroff.sh`).

**Verdict:** This feature is completely absent from pi-gen. See `UX-PARITY.md` for the implementation plan.

---

## 6. Debian / Python version

**pi-gen (current):** `RELEASE=bookworm` — Debian 12, released June 2023. Python 3.11.2. The current config is already running an outdated base: RPi OS trixie shipped October 2025 and is now the current release from Raspberry Pi.

**pi-gen (after trixie upgrade):** Debian 13, Python 3.13.5 (latest as of June 2026). Five-year support lifecycle to 2030.

**pistomp-arch:** Rolling release, currently tracking Python 3.11.11 via pyenv pin. Arch has shipped Python 3.13 in its rolling repos; adopting it requires changing one line in `config.sh` plus the mod-ui porting work.

**Verdict:** pi-gen-pistomp-after-trixie wins on currency (latest LTS Python, 5-year support). pistomp-arch is pinned to 3.11 and will need deliberate work to move. Neither gets Python 3.13 without the mod-ui tornado porting work.

---

## 7. RT kernel

**pi-gen:** Three pre-built `.deb` blobs committed directly to git (`linux-image-6.1.54-rt15-v8+`, headers, libc-dev; `linux-image-6.12.9-v8-16k+`). Large binaries in git. `03-run.sh` installs them via `dpkg -i` inside chroot then manually moves kernel files. `firstboot.sh` switches `config.txt` to activate the RT kernel — the device boots stock RPi kernel first, then reboots into RT. On trixie, these bookworm-era kernel packages need to be rebuilt against trixie's initramfs infrastructure.

**pistomp-arch:** `linux-rpi-rt` PKGBUILD + `build-rt-kernel-docker.sh`. RT kernel is a proper pacman package — installable/removable/pinnable. Currently ships `linux-rpi` (stock) with RT as an opt-in.

**Verdict:** pistomp-arch wins on architecture. Kernel blobs in git is a maintenance burden, and the two-boot firstboot sequence contributes to slow boot time. The trixie upgrade requires rebuilding these `.deb` files regardless.

---

## 8. User configuration / imager UX

**pi-gen:** Relies on the old RPi Imager 1.x customization mechanism (`userconf`, `cmdline.txt` pre-flash injection). `firstboot.sh` is placed on the boot partition and invoked by `firstboot.service`. The current version (`DISABLE_FIRST_BOOT_USER_RENAME=1`, `piwiz` removed) partially bypasses this but is still tied to pi-gen's user creation flow. RPi Imager 2.x changed the pre-flash customization flow; compatibility is unclear.

**pistomp-arch:** `pistomp.conf` on the FAT32 boot partition — plain text, editable in any text editor on any OS after flashing. Works identically with RPi Imager, Balena Etcher, `dd`, or anything else. File stays on the device after firstboot as documentation of what was applied. To re-apply: delete `/boot/firstboot.done` and reboot.

**Verdict:** pistomp-arch wins. `pistomp.conf` is simpler, more portable, and more transparent. See `UX-PARITY.md` for porting this paradigm to pi-gen.

---

## 9. Recovery and rollback

**pi-gen:** Nothing. No package rollback, no checkpoint mechanism, no recovery UI. Devices in the field have no recourse beyond reflashing.

**pistomp-arch:** pistomp-recovery is a full systemd service with LCD UI, per-domain git versioning (pedalboards, config, system, packages), pacman package rollback from on-device cache, and factory reset. Triggered automatically after 3 crashes in 3 minutes via `OnFailure=pistomp-recovery.service`.

**Verdict:** Complete absence in pi-gen. Requires significant infrastructure work to reach parity; see `PACKAGING.md` for the apt-side package rollback story.

---

## Summary

| Area | pi-gen (bookworm) | pi-gen (trixie) | pistomp-arch |
|---|---|---|---|
| Package tracking | None | None without debpkgs/ work | Full (pacman) |
| Broken upstream deps | sfizz, lilv, jack2 | sfizz still broken; jack2+lilv via apt | Override via PKGBUILD |
| Python isolation | Global pip mess | Global pip mess + porting work needed | Per-app venvs, pyenv |
| Python version | 3.11 | 3.13 (after porting work) | 3.11 (pyenv-pinned) |
| Boot time | 5+ min (restart loops) | Same until UX work done | ~1 min |
| LCD during boot | Blank | Blank until UX work done | Splash + progress |
| RT kernel | Blobs in git, extra reboot | Needs rebuild for trixie | PKGBUILD, clean |
| Imager UX | Old RPi 1.x flow | Old RPi 1.x flow | pistomp.conf, any flasher |
| Recovery/rollback | None | None | pistomp-recovery |
| Base OS currency | Outdated (bookworm) | Current (trixie, 2030 LTS) | Rolling |

The trixie upgrade closes the jack2 and lilv gaps and puts pi-gen on a supported, current base — but it is blocked on the tornado/mod-ui porting work and RT kernel rebuild. Everything else (package tracking, boot time, LCD, imager UX, recovery) requires additional targeted work documented in `UX-PARITY.md` and `PACKAGING.md`.
