# PLAN-3e: Integration Layer

Wires everything from PLAN-3a through PLAN-3d into the actual image build.

---

## 1. `scripts/fetch-packages.sh`

**Path:** `/scripts/fetch-packages.sh`

This script populates `cache/` before `build-docker.sh` runs. It is the
single entry point for obtaining all custom `.deb` files regardless of whether
a package is in phase 1 (local `debpkgs/` build) or phase 2 (download from
GitHub Releases).

```bash
#!/bin/bash
# Populate cache/ with all custom .deb files needed by the image build.
# Phase 1: build locally from debpkgs/<pkg>/build.sh
# Phase 2: download from GitHub Releases using <PKG>_DEB_REPO + <PKG>_DEB_VERSION
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CACHE_DIR="${CACHE_DIR:-${ROOT_DIR}/cache}"

source "${ROOT_DIR}/config.sh"

mkdir -p "${CACHE_DIR}"

# Registry of all custom packages.
# Format per entry: "PKG_NAME  PHASE1_BUILD_SH_EXISTS"
# Phase 1: debpkgs/<pkg>/build.sh exists → build locally
# Phase 2: <PKG>_DEB_REPO + <PKG>_DEB_VERSION vars exist → download

fetch_or_build() {
    local pkg="$1"
    local build_sh="${ROOT_DIR}/debpkgs/${pkg}/build.sh"

    # Derive upper-cased stem (jack2-pistomp → JACK2_PISTOMP)
    local stem
    stem="$(echo "${pkg}" | tr '[:lower:]-' '[:upper:]_')"
    local deb_repo_var="${stem}_DEB_REPO"
    local deb_ver_var="${stem}_DEB_VERSION"

    # Check cache first (skip unless FORCE_REBUILD=1)
    if ls "${CACHE_DIR}/${pkg}_"*"_arm64.deb" &>/dev/null && [[ -z "${FORCE_REBUILD:-}" ]]; then
        echo "==> ${pkg}: already in cache, skipping."
        return 0
    fi

    if [[ -f "${build_sh}" ]]; then
        # Phase 1: local build
        echo "==> ${pkg}: building from source (phase 1)..."
        CACHE_DIR="${CACHE_DIR}" WORKDIR=/tmp bash "${build_sh}"
    elif [[ -n "${!deb_repo_var:-}" && -n "${!deb_ver_var:-}" ]]; then
        # Phase 2: download from GitHub Releases
        local repo="${!deb_repo_var}"
        local version="${!deb_ver_var}"
        local url="https://github.com/${repo}/releases/download/${pkg}_${version}/${pkg}_${version}_arm64.deb"
        echo "==> ${pkg}: downloading from ${url}..."
        curl -fsSL -o "${CACHE_DIR}/${pkg}_${version}_arm64.deb" "${url}"
    else
        echo "ERROR: ${pkg} has no build.sh and no _DEB_REPO/_DEB_VERSION in config.sh" >&2
        exit 1
    fi
}

# All custom packages, in dependency order (hylia before mod-host-pistomp)
PACKAGES=(
    hylia
    jack2-pistomp
    mod-host-pistomp
    amidithru
    mod-midi-merger
    mod-ttymidi
    sfizz-pistomp
    fluidsynth-headless
    lcd-splash
    jack-capture
    pi-stomp
    mod-ui
)

for pkg in "${PACKAGES[@]}"; do
    fetch_or_build "${pkg}"
done

echo "==> fetch-packages.sh complete. Cache contents:"
ls "${CACHE_DIR}/"*.deb 2>/dev/null || echo "  (none)"
```

**Notes:**
- `hylia` must appear before `mod-host-pistomp` in the list. `debpkgs/mod-host-pistomp/build.sh` installs `cache/hylia_*.deb` before calling `dpkg-buildpackage` so that `liblibhylia.so` is available during build. This is a build-time dep only.
- `FORCE_REBUILD=1` causes re-download (phase 2) or re-build (phase 1).
- The script must run outside Docker (on the host), before `build-docker.sh`, so `cache/` is populated for the Docker bind-mount.

---

## 2. `02-run.sh` transition

**File:** `stage2/05-pistomp/02-run.sh`

### What gets deleted

Every source-build block in the current `on_chroot` body is removed:

| Current block | Lines in current file | Replacement |
| :--- | :--- | :--- |
| `pip3 install uv` + `curl waf` | 13–16 | Keep `pip3 install uv` only (needed for stage3's `uv sync`). Remove `curl waf` — waf is no longer needed at image build time. |
| `UV_PYTHON_INSTALL_DIR=... uv python install 3.11` | 19 | Remove — Python 3.11 venv is built by the `mod-ui` `.deb`. |
| `Hylia` clone + make + make install | 22–26 | Delete. Replaced by `apt-get install -y hylia`. |
| `jack2` clone + patch + waf | 28–40 | Delete. Replaced by `apt-get install -y jack2-pistomp`. |
| `jack-example-tools` clone + meson | 43–48 | Delete. Replaced by `apt-get install -y jack-example-tools` (from Trixie). |
| `browsepy` clone + pip install | 53–56 | **Keep.** No `.deb` for browsepy — pip install stays. |
| `mod-host` clone + make | 58–61 | Delete. Replaced by `apt-get install -y mod-host-pistomp`. |
| `mod-ui` clone + venv + tornado install | 64–79 | Delete. Replaced by `apt-get install -y mod-ui`. |
| `amidithru` clone + make | 81–85 | Delete. Replaced by `apt-get install -y amidithru`. |
| `touchosc2midi` clone + pip install | 87–90 | **Keep.** No `.deb` for touchosc2midi — pip install stays. |
| `mod-midi-merger` clone + cmake | 92–101 | Delete. Replaced by `apt-get install -y mod-midi-merger`. |
| `mod-ttymidi` clone + make | 103–106 | Delete. Replaced by `apt-get install -y mod-ttymidi`. |
| `rm -f /tmp/pi-controller-reset.patch` | 108 | Delete — patch is no longer staged to `/tmp`. |

Also remove the outer `install -m 644 files/patches/pi-controller-reset.patch "${ROOTFS_DIR}/tmp/"` line
(line 4, outside the `on_chroot` block) — the patch is now applied at `.deb` build time.

### What the new `on_chroot` block contains

```bash
#!/bin/bash -e

# shellcheck source=../../config.sh
source "$(dirname "${BASH_SOURCE[0]}")/../../config.sh"

echo "Installing MOD software"
on_chroot << EOF

mkdir -p /home/${FIRST_USER_NAME}/tmp
cd /home/${FIRST_USER_NAME}/tmp

# uv: Python version manager + used in stage3 for pi-stomp venv
pip3 install uv

# Add pistomp apt repository
echo "deb [arch=arm64 trusted=yes] https://treefallsound.github.io/pi-gen-pistomp trixie main" \
    > /etc/apt/sources.list.d/pistomp.list
apt-get update -qq

# Install all custom pistomp debs in one pass (apt resolves deps).
# jack-example-tools comes from Trixie; the rest come from the pistomp apt repo.
apt-get install -y \
    jack-example-tools \
    hylia \
    jack2-pistomp \
    mod-host-pistomp \
    amidithru \
    mod-midi-merger \
    mod-ttymidi \
    sfizz-pistomp \
    fluidsynth-headless \
    lcd-splash \
    jack-capture \
    mod-ui

# browsepy: no .deb; pip install from source
[ ! -d browsepy ] && git clone ${BROWSEPY_REPO}
cd browsepy
pip3 install ./
cd ..

# touchosc2midi: no .deb; pip install from source
[ ! -d touchosc2midi ] && git clone ${TOUCHOSC2MIDI_REPO}
cd touchosc2midi
pip3 install ./
cd ..

EOF
```

**Sequencing note:** The `apt-get install` block above runs inside the chroot.
The `cache/` directory is not available inside the chroot — all packages must be
available via the pistomp apt repo by the time `build-docker.sh` runs. This
means `fetch-packages.sh` (which populates `cache/`) is a prerequisite, and the
`publish-apt-repo.yml` workflow (which serves them via gh-pages) must have
already run for those packages.

**Alternative for local/CI builds before the apt repo is live:** The `dpkg -i`
approach can be used temporarily. Mount `cache/` into the Docker build and in
`02-run.sh` do:

```bash
# Temporary: install directly from cache/ bind-mounted at /pistomp-cache/
dpkg -i /pistomp-cache/hylia_*.deb
dpkg -i /pistomp-cache/jack2-pistomp_*.deb
# ... etc.
apt-get install -f -y   # resolve any remaining deps
```

Once the apt repo is live on gh-pages, switch to the `apt-get install` form.

---

## 3. Stage3 transition

**Files:**
- `stage3/01-pistomp/01-run.sh` — replace git clone + uv venv block
- `stage3/01-pistomp/02-run.sh` — delete entirely (or leave as no-op)

### New `stage3/01-pistomp/01-run.sh`

Replace the current git clone + venv creation block with:

```bash
on_chroot << EOF

# pi-stomp installed as .deb; postinst creates /home/pistomp/pi-stomp symlink
# pointing to /opt/pistomp/pi-stomp/ and enables mod-ala-pi-stomp.service.
apt-get install -y pi-stomp

# data dir (still needed for user data that lives outside the package)
mkdir -p /home/${FIRST_USER_NAME}/data/config
mkdir -p /usr/mod/scripts

# pi-Stomp user-files (user-editable; not shipped in .deb)
git clone --recurse-submodules ${USERFILES_REPO} /home/${FIRST_USER_NAME}/data/user-files

# Config templates come from the installed package path, not the old git clone path
install -m 644 /opt/pistomp/pi-stomp/setup/config_templates/default_config.yml \
    /home/${FIRST_USER_NAME}/data/config/
install -m 644 /opt/pistomp/pi-stomp/setup/config_templates/default-hardware-descriptor.json \
    /home/${FIRST_USER_NAME}/data/config/

# Pedalboards (user-editable; not shipped in .deb — .deb postinst does NOT clone these)
rm -rf /home/${FIRST_USER_NAME}/data/.pedalboards
git clone ${PEDALBOARDS_REPO} /home/${FIRST_USER_NAME}/data/.pedalboards
ln -s /home/${FIRST_USER_NAME}/data/.pedalboards /home/${FIRST_USER_NAME}/.pedalboards

# mod-tweaks script: copy from installed package location
install -m 755 /opt/pistomp/pi-stomp/setup/mod-tweaks/start_touchosc2midi.sh /usr/mod/scripts/

# LV2 plugins
mkdir -p /home/${FIRST_USER_NAME}/tmp
pushd /home/${FIRST_USER_NAME}/tmp
wget ${LV2_PLUGINS_URL}
tar -zxf lv2plugins.tar.gz -C /home/${FIRST_USER_NAME}/
ln -s /home/${FIRST_USER_NAME}/.lv2 /home/${FIRST_USER_NAME}/data/.lv2
popd
rm -rf /home/${FIRST_USER_NAME}/tmp

EOF
```

### Delete `stage3/01-pistomp/02-run.sh`

The `uv sync` step in `02-run.sh` is no longer needed — the pi-stomp `.deb`
build process creates and populates the venv at `/opt/pistomp/venvs/pi-stomp/`
at package build time. Delete this file (or replace with a comment-only stub).

### Version info block

The end of `01-run.sh` currently calls:
```bash
git --work-tree /home/${FIRST_USER_NAME}/pi-stomp --git-dir /home/${FIRST_USER_NAME}/pi-stomp/.git describe ...
```
With the symlink in place (`/home/pistomp/pi-stomp` → `/opt/pistomp/pi-stomp`), this
call still works. However, the `.git` directory is no longer present at the
installed path (the `.deb` ships source files, not a git repo). Replace with:

```bash
software_version=$(on_chroot <<EOF
dpkg-query -W -f='${Version}' pi-stomp
EOF
)
```

---

## 4. `factory-packages.list`

After all custom debs are installed, record installed versions for
pistomp-recovery's factory-reset baseline.

**Install location:** `/etc/pistomp/factory-packages.list`

**Run in:** `stage3/01-pistomp/01-run.sh` (after the `apt-get install pi-stomp` block and
all other package installs in stage2), or in a dedicated `stage3/01-pistomp/03-run.sh`.

**Package list** (all 15 from `pistomp-recovery`'s `PISTOMP_PACKAGES_DEBIAN`):

```bash
on_chroot << EOF

mkdir -p /etc/pistomp

dpkg-query -W -f='{"${Package}": "${Version}"}\n' \
    hylia \
    jack2-pistomp \
    mod-host-pistomp \
    amidithru \
    mod-midi-merger \
    mod-ttymidi \
    sfizz-pistomp \
    fluidsynth-headless \
    lcd-splash \
    jack-capture \
    pi-stomp \
    mod-ui \
    pistomp-recovery \
    jack-example-tools \
    touchosc2midi \
    | python3 -c "
import sys, json
pkgs = {}
for line in sys.stdin:
    line = line.strip()
    if line:
        pkgs.update(json.loads(line))
print(json.dumps(pkgs, indent=2))
" > /etc/pistomp/factory-packages.list

EOF
```

Note: `touchosc2midi` and `pistomp-recovery` are pip-installed / separately
packaged. If they are not installed as `.deb` at image-build time, `dpkg-query`
will error on those names — guard with `dpkg -l <pkg> &>/dev/null && echo ...`
or filter the output with `|| true` per package.

---

## 5. apt sources setup

**File:** `/etc/apt/sources.list.d/pistomp.list`

This is written inside the `on_chroot` block at the **top of `stage2/05-pistomp/02-run.sh`**,
before any `apt-get install` of pistomp packages:

```bash
echo "deb [arch=arm64 trusted=yes] https://treefallsound.github.io/pi-gen-pistomp trixie main" \
    > /etc/apt/sources.list.d/pistomp.list
apt-get update -qq
```

**GPG key hook point:** When GPG signing is added to the apt repo, change the
source line to:

```
deb [arch=arm64 signed-by=/usr/share/keyrings/pistomp-archive-keyring.gpg] \
    https://treefallsound.github.io/pi-gen-pistomp trixie main
```

and add a step before the `echo` that installs the public key:

```bash
install -m 644 files/pistomp-archive-keyring.gpg \
    "${ROOTFS_DIR}/usr/share/keyrings/pistomp-archive-keyring.gpg"
```

The key file would be checked into `stage2/05-pistomp/files/`.

---

## 6. Sudoers entry

Per PLAN-3a §6, install the sudoers drop-in in `stage2/05-pistomp/03-run.sh`
(the same script that installs networking files and the RT kernel).

Add this line **outside** the `on_chroot` block, alongside the other `install`
calls at the top of `03-run.sh`:

```bash
install -m 440 files/pistomp-nopasswd.sudoers \
    "${ROOTFS_DIR}/etc/sudoers.d/pistomp-nopasswd"
```

**File:** `stage2/05-pistomp/files/pistomp-nopasswd.sudoers`

```
# Allow the pistomp user to run package management without a password.
# Required by pistomp-recovery to perform OTA upgrades.
pistomp ALL=(ALL) NOPASSWD: /usr/bin/apt-get, /usr/bin/dpkg, /usr/bin/apt
```

---

## 7. `build-docker.sh` integration

`fetch-packages.sh` must run **on the host**, before Docker starts, so that
`cache/` is populated. It is called as a preamble in `build-docker.sh`:

```bash
# Near the top of build-docker.sh, after the CONTINUE / config file checks:
echo "==> Fetching/building custom .deb packages..."
bash "${DIR}/scripts/fetch-packages.sh"
```

**Why preamble (not separate documented step):** The RT kernel build is a
separate documented prerequisite (`build-rt-kernel-docker.sh`) because it
takes 20–40 minutes and its output is cached long-term. Custom debpkg builds
are much faster (seconds to minutes) and the cache check in `fetch-packages.sh`
makes re-runs cheap. Embedding it in `build-docker.sh` reduces the chance of
a user starting a Docker build without a populated cache.

**`cache/` bind-mount into Docker:** The Docker build container currently does
not mount `cache/`. Add a bind-mount flag to the `docker run` invocation in
`build-docker.sh`:

```bash
# Existing docker run flags (paraphrased):
#   -v "${DIR}:/pi-gen"
# Add alongside them:
#   -v "${DIR}/cache:/pi-gen/cache:ro"
```

This makes `cache/*.deb` available inside the build at `/pi-gen/cache/`. The
`02-run.sh` `dpkg -i` path (used before the apt repo is live) can reference
`/pi-gen/cache/` directly.

---

## 8. Service file updates

Per PLAN-3d §5, the following service files need path updates when pi-stomp
and mod-ui move to `/opt/pistomp/`:

### `stage2/05-pistomp/files/services/mod-ala-pi-stomp.service`

```
# Before:
ExecStart=/opt/pistomp/venvs/pi-stomp/bin/python /home/pistomp/pi-stomp/modalapistomp.py

# After (pi-stomp .deb postinst creates /home/pistomp/pi-stomp → /opt/pistomp/pi-stomp symlink,
# so both paths work, but use the canonical path):
ExecStart=/opt/pistomp/venvs/pi-stomp/bin/python /opt/pistomp/pi-stomp/modalapistomp.py
```

### `stage2/05-pistomp/files/services/mod-ui.service`

```
# Before:
Environment=MOD_HTML_DIR=/opt/mod-ui-venv/share/mod/html
ExecStartPre=/usr/local/bin/wait-for-mod-host.sh
ExecStart=/usr/bin/authbind /opt/mod-ui-venv/bin/mod-ui

# After:
Environment=MOD_HTML_DIR=/opt/pistomp/mod-ui/html
ExecStartPre=/usr/local/bin/wait-for-mod-host.sh
ExecStart=/usr/bin/authbind /opt/pistomp/venvs/mod-ui/bin/mod-ui
```

### `stage2/05-pistomp/files/services/mod-host.service`

```
# Before:
ExecStart=/usr/local/bin/mod-host -p 5555 -f 5556

# After (apt package installs to /usr/bin/):
ExecStart=/usr/bin/mod-host -p 5555 -f 5556
```

### `stage2/05-pistomp/files/services/mod-amidithru.service`

```
# Before:
ExecStart=/usr/local/bin/amidithru touchosc

# After:
ExecStart=/usr/bin/amidithru touchosc
```

### `stage2/05-pistomp/files/services/ttymidi.service`

```
# Before:
ExecStart=/usr/local/bin/ttymidi -s /dev/ttyAMA0 -b 38400

# After:
ExecStart=/usr/bin/ttymidi -s /dev/ttyAMA0 -b 38400
```

### `stage2/05-pistomp/files/services/mod-midi-merger.service` and `mod-midi-merger-broadcaster.service`

Per PLAN-3b §4, `jack-example-tools` from Trixie apt installs to `/usr/bin/`:

```
# Before:
ExecStart=/usr/local/bin/jack_load mod-midi-merger
ExecStop=/usr/local/bin/jack_unload mod-midi-merger

# After:
ExecStart=/usr/bin/jack_load mod-midi-merger
ExecStop=/usr/bin/jack_unload mod-midi-merger
```

Same change applies to `mod-midi-merger-broadcaster.service`:

```
# Before:
ExecStart=/usr/local/bin/jack_load mod-midi-broadcaster
ExecStop=/usr/local/bin/jack_unload mod-midi-broadcaster

# After:
ExecStart=/usr/bin/jack_load mod-midi-broadcaster
ExecStop=/usr/bin/jack_unload mod-midi-broadcaster
```

### `stage2/05-pistomp/01-run.sh` — service symlinks

The current `01-run.sh` enables `mod-ala-pi-stomp.service` from `stage3/01-pistomp/01-run.sh`
(line 39). With the pi-stomp `.deb`, its `postinst` enables the service via a
`/etc/systemd/system/multi-user.target.wants/` symlink. Remove the explicit `ln -sf` for
`mod-ala-pi-stomp.service` from the stage3 script. The `01-run.sh` service
symlinks in stage2 (jack.service, mod-host.service, mod-ui.service, etc.) remain —
those are enabled here rather than in `.deb` postinst scripts, since they are
stage2 system services that will always be present.

---

## 9. Sequencing summary

End-to-end order of operations for a clean build:

1. **`./build-rt-kernel-docker.sh`** (once, skip if `files/sys/*.deb` already exist).
2. **`./scripts/fetch-packages.sh`** (run by `build-docker.sh` as preamble; skips cached debs).
   - Inside this: `hylia` builds first → `mod-host-pistomp` build.sh installs `cache/hylia_*.deb` before compiling.
3. **`./build-docker.sh`** — runs pi-gen stages inside Docker.
   - Stage0–1: Bootstrap.
   - Stage2/01-sys-tweaks: `00-packages` apt install (build tools, libfluidsynth3, etc.).
   - Stage2/05-pistomp/01-run.sh: service files, groups, `data/` dir.
   - Stage2/05-pistomp/02-run.sh: apt pistomp repo added; all custom debs installed; browsepy + touchosc2midi pip-installed.
   - Stage2/05-pistomp/03-run.sh: sudoers drop-in, RT kernel, networking files.
   - Stage2/05-pistomp/04-run.sh: firstboot, chown.
   - Stage3/01-pistomp/01-run.sh: `apt-get install pi-stomp`; pedalboards/user-files git clones; LV2 plugins; `factory-packages.list`.

**Critical dependency:** `hylia` must be in `cache/` before `mod-host-pistomp` build.sh runs (step 2). `fetch-packages.sh` processes them in order, and `debpkgs/mod-host-pistomp/build.sh` must `dpkg -i "${CACHE_DIR}/hylia_"*.deb` before calling `dpkg-buildpackage`.
