# PLAN-3b: Apt vs Source-Build Audit for Stage 2 Packages

Audit of which packages can be replaced with `apt install` on Debian Trixie (stable, released
2025-08-09), arm64 architecture.

---

## 1. Summary Table

| Package | Apt package name | Version in Trixie | arm64? | Verdict |
|---|---|---|---|---|
| jack_capture | — | not in trixie | — | Build custom deb |
| lgpio / lg | `python3-rpi-lgpio` (already in 00-packages) | — | yes | Already using apt |
| fluidsynth-headless | `fluidsynth` + `libfluidsynth3` (already in 00-packages) | 2.4.4+dfsg-1+deb13u2 | yes | Already using apt (see note) |
| libfluidsynth2-compat | n/a — Trixie ships libfluidsynth3 | 2.4.4+dfsg-1+deb13u2 | yes | Not needed |
| jack-example-tools | `jack-example-tools` | 4-4 | yes | **Use apt** |
| amidithru | — | not in trixie | — | Build custom deb |
| mod-ttymidi | — | not in trixie | — | Build custom deb |
| mod-midi-merger | — | not in trixie | — | Build custom deb |
| hylia | — | not in trixie | — | Build custom deb |

---

## 2. Notes on Packages Already Handled via Apt

### lgpio / lg
`python3-rpi-lgpio` is already listed in `stage2/01-sys-tweaks/00-packages` line 8. Nothing to do.

### fluidsynth / libfluidsynth3
`libfluidsynth3` and `libfluidsynth-dev` are already in `stage2/01-sys-tweaks/00-packages` lines
41–42. The `fluidsynth` CLI binary is a separate package; if it is needed at runtime, it can be
added to `00-packages`.

**SDL2 caveat**: The Trixie `fluidsynth` package links against libsdl2. SDL2 requires either a
display or `SDL_VIDEODRIVER=offscreen` to initialise. pi-Stomp runs headless — if fluidsynth is
invoked directly (not via the library), it will fail unless invoked with JACK as the audio driver
(`-a jack`) and without SDL initialisation. The library path (`libfluidsynth3`) does not have this
problem because libfluidsynth initialises only the audio backend you specify; SDL2 is only activated
when fluidsynth is configured to use SDL as its audio driver. Verdict: safe to use `apt install
fluidsynth` as long as pi-Stomp passes `-a jack` or `alsa` on the command line.

### libfluidsynth2-compat
This was a shim for LV2 plugins compiled against libfluidsynth.so.2. Trixie ships
libfluidsynth.so.3 (from `libfluidsynth3`). The LV2 plugins in the image were audited separately
(`lv2-report.json`): 23 plugins load `libfluidsynth.so.2`. If those plugins are arm64 binaries
compiled against version 2, they will fail to load on Trixie unless a compat shim is provided.
This is an existing known issue tracked separately; it is not changed by this audit.

---

## 3. Packages Not in Trixie — Custom Build Required

### jack_capture
Dropped from Trixie stable. Present in `forky` (next testing cycle, v0.9.73-5) and
`sid` (v0.9.73-5). The Trixie package list for the `sound` section does not include it.

**Options**:
- Backport `jack_capture` from sid/forky: clone the source package and build against Trixie.
- Build from upstream https://github.com/kmatheussen/jack_capture (minimal deps: libjack, libsndfile).
- Defer: jack_capture is not referenced anywhere in the current `stage2` build scripts. If
  pi-Stomp does not use it, skip entirely.

**Recommendation**: Check whether pi-Stomp actually calls jack_capture. If not referenced in
stage3 or runtime config, omit it entirely.

### amidithru
Not in Trixie or any current Debian suite. Upstream is
https://github.com/BlokasLabs/amidithru — a Blokas-maintained C++ binary with a simple Makefile.
The current `02-run.sh` builds it from source (lines 79–82, including a Makefile patch).
Continue building from source; the build is fast and trivial.

### mod-ttymidi
Not in any Debian suite. Upstream: https://github.com/moddevices/mod-ttymidi.
Current `02-run.sh` builds it from source (lines 101–103). Continue building from source.

### mod-midi-merger
Not in any Debian suite. Upstream: https://github.com/mod-audio/mod-midi-merger.
Current `02-run.sh` builds it from source (lines 90–98) with a cmake prefix override.
Continue building from source.

### hylia
Not in any Debian suite. Upstream is a JACK-specific wrapper around Ableton Link:
https://github.com/falkTX/Hylia. There is no `liblink` or `libablton-link` Debian package.
Current `02-run.sh` clones and makes it (lines 20–24). Continue building from source.

---

## 4. Changes to 02-run.sh

### Replace with apt

**jack-example-tools** (lines 41–46 in `02-run.sh`):

```bash
# REMOVE this block:
[ ! -d jack-example-tools ] && git clone --branch debian/4-4 https://salsa.debian.org/multimedia-team/jack-example-tools.git
cd jack-example-tools
meson setup --prefix=/usr/local build
ninja -C build
meson install -C build
cd ..
```

Add `jack-example-tools` to `stage2/01-sys-tweaks/00-packages` instead.

**Important**: The existing service files reference `/usr/local/bin/jack_load` and
`/usr/local/bin/jack_unload`. The apt package installs these to `/usr/bin/`. Update the service
files accordingly:

- `stage2/05-pistomp/files/services/mod-midi-merger.service` lines 9–10:
  change `/usr/local/bin/jack_load` → `/usr/bin/jack_load`
  change `/usr/local/bin/jack_unload` → `/usr/bin/jack_unload`

### No change needed
All other source-build blocks in `02-run.sh` (Hylia, jack2, amidithru, mod-midi-merger,
mod-ttymidi) have no apt equivalent in Trixie and must stay as source builds.

---

## 5. Uncertain / Recommend Runtime Test

### fluidsynth SDL2 + headless
The `fluidsynth` CLI binary in Trixie depends on libsdl2. On a headless system with no
`$DISPLAY`, SDL2 may attempt to initialise a video subsystem and fail. Test by running
`fluidsynth -a jack -m alsa_seq` on the built image before shipping. If it fails, either:
- Set `SDL_VIDEODRIVER=offscreen` in the service environment, or
- Build a custom fluidsynth .deb with `--disable-sdl2`.

The library (`libfluidsynth3`) is unaffected — it only activates the SDL2 driver if explicitly
configured, and pi-Stomp links against the library, not the CLI.

### jack-example-tools install prefix
The existing source build installs to `/usr/local/`. The apt package installs to `/usr/`. Verify
that no other script or service hardcodes `/usr/local/bin/jack_*` beyond the two service files
noted above.
