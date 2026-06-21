# Packaging Strategy for pi-gen-pistomp

## Why we're doing this

The current `stage2/05-pistomp/02-run.sh` builds all native C components by cloning git repos and running `make install` directly into `/usr/local/`. This works for a single image build but has compounding problems as the project matures:

**No package tracking.** Once a component is installed there is no clean way to upgrade or remove it. `dpkg -l` doesn't know sfizz exists. Recovery tooling can't roll back what dpkg doesn't own.

**Upstream packages are broken or too old.** Debian bookworm ships sfizz 1.1.1 (2021), which segfaults at runtime on our hardware. We need 1.2.3+ with specific CMake flags (no system abseil/pugixml, no LV2 UI, headless). We can't `apt install sfizz` and we can't `apt install sfizz=1.2.3` either — we need to build our own. The same pattern applies to jack2, lilv, mod-host, and others: upstream Debian versions are either too old, conflict with each other, or lack compile-time options we require.

**No upgrade path for deployed devices.** Devices in the field have no way to pull a fixed build of sfizz without reflashing. The pistomp-recovery package rollback model (which works cleanly on the Arch side via pacman) has no Debian equivalent unless dpkg owns the packages.

**Build time is dominated by C++ compilation.** Every image build recompiles jack2, sfizz, lilv, mod-host from source inside a chroot — even when nothing changed. This is slow and fragile (network access during chroot, OOM risk on heavy C++ templates).

**The goal:** decouple C component builds from image assembly, track all custom packages via dpkg, and give deployed devices a clean upgrade and rollback path.

---

## Approach: fork + CI packages

The pattern that fixes all of the above:

```
GitHub fork of upstream       →   .deb built in CI   →   our apt repo   →   image build   →   device apt update
(our patches as commits)          (arm64, tagged)         (GitHub Pages)     (apt install)      (pistomp-recovery)
```

This mirrors exactly what pistomp-arch already does for Arch Linux (PKGBUILDs → pacman repo on GitHub Releases → pacstrap/pacman).

### 1. Fork structure

For each upstream package we need to patch or pin, create a fork in the `TreeFallSound` GitHub org:

```
TreeFallSound/sfizz           # fork of sfztools/sfizz-ui, tag 1.2.3-pistomp-1
TreeFallSound/mod-host        # fork of mod-audio/mod-host
TreeFallSound/jack2           # fork of jackaudio/jack2 (or pin via debian/ only)
```

Apply our patches as commits on a branch (e.g. `pistomp`). This makes the diff visible in GitHub, allows upstream comparisons with `git log upstream/master..pistomp`, and gives each change a commit message explaining why it exists.

For packages we don't patch but merely pin to a specific version (jack2, lilv), a fork is optional — a `debian/` directory in this repo is enough.

### 2. Building arm64 .deb packages in CI

Since we're on GitHub Free (no native arm64 runners), use cross-compilation:

```yaml
# .github/workflows/build-sfizz.yml
runs-on: ubuntu-latest
steps:
  - uses: actions/checkout@v4
    with:
      repository: TreeFallSound/sfizz
      ref: 1.2.3-pistomp-1
      submodules: recursive

  - name: Install cross toolchain
    run: |
      sudo apt-get install -y crossbuild-essential-arm64 cmake debhelper devscripts
      echo "deb [arch=arm64] http://ports.ubuntu.com/ubuntu-ports noble main" | \
        sudo tee -a /etc/apt/sources.list
      sudo dpkg --add-architecture arm64
      sudo apt-get update
      sudo apt-get install -y libsndfile1-dev:arm64 libsamplerate0-dev:arm64 lv2-dev:arm64

  - name: Build
    env:
      DEB_BUILD_OPTIONS: nocheck  # don't try to run arm64 test binaries on x86
    run: dpkg-buildpackage --host-arch arm64 -b -us -uc

  - name: Upload artifact
    uses: actions/upload-artifact@v4
    with:
      name: sfizz-pistomp-deb
      path: ../*.deb
```

`DEB_BUILD_OPTIONS=nocheck` is required — without it, `dh_auto_test` will try to execute the built aarch64 binaries on the x86 runner and segfault. CMake-based packages (sfizz, mod-host) cross-compile cleanly with debhelper because `dh_auto_configure` passes `--host` correctly.

QEMU-based approaches (`run-on-arch-action`, `docker buildx`) work but are 3–5× slower. sfizz with `-j4` in QEMU could take 45–90 minutes vs ~15 minutes cross-compiled.

### 3. Publishing to our apt repo

Trigger a publish workflow on each package release. The index lives on GitHub Pages (lightweight, free); the `.deb` files are stored as GitHub Releases assets (no Pages storage quota impact).

```yaml
# .github/workflows/publish-apt-repo.yml
- name: Download all package artifacts
  uses: actions/download-artifact@v4

- name: Update apt repo index
  run: |
    # Collect debs into pool/
    mkdir -p repo/pool/main repo/dists/stable/main/binary-arm64
    find . -name '*.deb' -exec cp {} repo/pool/main/ \;

    # Generate Packages index (--multiversion keeps old versions for rollback)
    dpkg-scanpackages --arch arm64 --multiversion repo/pool/main/ \
      > repo/dists/stable/main/binary-arm64/Packages
    gzip -k repo/dists/stable/main/binary-arm64/Packages

    # Generate and sign Release file
    apt-ftparchive release repo/dists/stable/ > repo/dists/stable/Release
    gpg --clearsign -o repo/dists/stable/InRelease repo/dists/stable/Release

- name: Deploy to GitHub Pages
  uses: peaceiris/actions-gh-pages@v4
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: repo
    keep_files: true   # accumulates versions across deploys
```

**GPG key management:** generate a repo signing key once, store the armored private key in a GitHub Actions secret. Bake the public key into images at build time (`/etc/apt/trusted.gpg.d/pistomp.gpg`). Devices never need to fetch the key — it's already in the image.

**`--multiversion` is non-negotiable** for the rollback story. `reprepro` (the most common recommendation) silently enforces one version per package — skip it. `dpkg-scanpackages --multiversion` keeps every `.deb` ever published in the `pool/` directory accessible by exact version string.

The resulting `sources.list` entry on devices:
```
deb [arch=arm64 signed-by=/etc/apt/trusted.gpg.d/pistomp.gpg] \
    https://treefallsound.github.io/pistomp-apt-repo stable main
```

### 4. Image builder becomes a consumer

Once packages are published, `02-run.sh` shrinks to:

```bash
on_chroot << EOF
apt-get install -y \
    sfizz-pistomp=1.2.3-1 \
    mod-host-pistomp=0.13.0-2 \
    jack2-pistomp=1.9.22-3 \
    lilv-pistomp=0.24.12-1
EOF
```

Pin exact versions. Commit a `packages.lock` in this repo alongside each image release so the image build is reproducible and you can bisect regressions by version. The image builder no longer needs `cmake`, `git`, build toolchains, or network access to upstream repos — just our apt repo.

For dev iteration (actively patching sfizz): build the `.deb` locally with `dpkg-buildpackage -b -us -uc`, then in the image build use:
```bash
install -m 644 sfizz-pistomp_*.deb ${ROOTFS_DIR}/tmp/
on_chroot << EOF
apt-get install -y --allow-downgrades /tmp/sfizz-pistomp_*.deb
EOF
```

This keeps the release pipeline clean while letting you test local changes without waiting for CI.

### 5. Device updates and rollback

At the time pistomp-recovery creates a checkpoint stamp, it should also cache the installed `.deb` files for rollback:

```bash
# run at stamp time
for pkg in sfizz-pistomp mod-host-pistomp jack2-pistomp; do
    ver=$(dpkg-query -W -f='${Version}' "$pkg")
    apt-get download "${pkg}=${ver}" -o Dir::Cache=/opt/pistomp/pkg-cache/
done
```

Recovery rollback then uses `dpkg -i /opt/pistomp/pkg-cache/<pkg>_<stamped-version>_arm64.deb` followed by `apt-get -f install --no-install-recommends`. This works offline, does not require the apt repo to be reachable, and mirrors the pacman cache rollback that already works on the Arch side.

`apt rollback` (a native apt feature) only exists in APT ≥ 3.2, which is not in Debian bookworm. Do not rely on it.

---

## Reference implementation: sfizz-pistomp

`debpkgs/sfizz-pistomp/` in this repo contains the prototype `debian/` directory and `build.sh`. This is the template to follow for other components. Key decisions encoded in it:

- `PLUGIN_LV2_UI=OFF`, `PLUGIN_VST3=OFF`, `SFIZZ_JACK=OFF` — headless, no GUI deps
- `SFIZZ_USE_SYSTEM_ABSEIL=OFF`, `SFIZZ_USE_SYSTEM_PUGIXML=OFF` — bookworm's versions trigger compile errors
- `debian/patches/add-mod-filetype.patch` — adds `mod:fileTypes` to the LV2 .ttl so mod-ui's file browser filters correctly
- `DEB_BUILD_OPTIONS=nocheck` in the CI workflow — prevents test execution on cross-builds
- Parallel jobs capped at 4 in `debian/rules` — sfizz's C++ templates OOM with unconstrained `-j`

When we move to the fork model, the patch moves from `debian/patches/` into a commit on `TreeFallSound/sfizz@pistomp`, and `build.sh` becomes a CI workflow that clones that fork at the tagged commit.
