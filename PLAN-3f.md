# PLAN-3f: RT Kernel as a debpkg

Move the RT kernel build into the `debpkgs/` monorepo pattern, retiring
`build-rt-kernel-docker.sh` as a standalone script.

---

## Motivation

`build-rt-kernel-docker.sh` is a one-off pre-build step that lives outside
the `debpkgs/` pattern. Folding it in gives:
- A single `fetch-packages.sh` invocation handles all packages including the kernel
- `config.sh` already owns the version pins (`KERNEL_VERSION`, `LINUX_RPI_COMMIT`, etc.) — no duplication
- Phase 2 transition works identically: swap source refs for `LINUX_RPI_RT_DEB_REPO` + `LINUX_RPI_RT_DEB_VERSION` when TreeFallSound publishes pre-built kernel .debs

---

## Key difference from other debpkgs

The kernel self-packages via `make bindeb-pkg` — it produces correctly-named
`.deb` files without a `debian/` tree. `debpkgs/linux-rpi-rt/` therefore
contains only `build.sh` (and a `README.md`). This is a valid deviation from
the template; note it in `debpkgs/README.md`.

---

## Structure

```
debpkgs/linux-rpi-rt/
  build.sh        ← all build logic; no debian/ tree
  README.md       ← notes the self-packaging deviation
rt-kernel/
  Dockerfile      ← unchanged (cross-compilation toolchain)
  diffconfig      ← unchanged (PREEMPT_RT config fragment)
```

---

## `debpkgs/linux-rpi-rt/build.sh`

Sources `config.sh` for version pins. Detects environment and chooses
build path:

```bash
#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${ROOT_DIR}/config.sh"

CACHE_DIR="${CACHE_DIR:-${ROOT_DIR}/cache}"
SOURCE_CACHE="${ROOT_DIR}/.kernel-cache"
KERNEL_RELEASE="${KERNEL_VERSION}${KERNEL_LOCALVERSION}"
PKG_GLOB="${CACHE_DIR}/linux-image-${KERNEL_RELEASE}_*.deb"

mkdir -p "${CACHE_DIR}" "${SOURCE_CACHE}"

# Cache check (skip unless FORCE_REBUILD=1)
if [[ "${FORCE_REBUILD:-0}" != "1" ]] && ls ${PKG_GLOB} &>/dev/null; then
    echo "==> RT kernel already in cache, skipping build."
    exit 0
fi
```

**Build path selection:**
```bash
if [[ "$(uname -m)" == "aarch64" ]]; then
    # Native arm64 (CI runner or M-series Mac with native env) — build directly
    _build_native
else
    # x86_64 or arm64 Mac without native toolchain — use Docker
    _build_docker
fi
```

`_build_native` runs the configure + `make bindeb-pkg` directly.
`_build_docker` is the existing `build-rt-kernel-docker.sh` logic, inlined.

Both paths output `.deb` files to `CACHE_DIR` (not `stage2/05-pistomp/files/sys/`).

---

## `config.sh` additions

The kernel variables are already present. Add `KERNEL_LOCALVERSION` if not
already there (currently inline in `build-rt-kernel-docker.sh` as `LOCALVERSION`):

```bash
KERNEL_LOCALVERSION="-rt-v8+"
```

Remove `JACK_EXAMPLE_TOOLS_REPO` / `JACK_EXAMPLE_TOOLS_REF` from `config.sh`
— jack-example-tools comes from Trixie apt, no longer needs a source ref.

---

## `stage2/05-pistomp/03-run.sh` changes

Currently installs from `files/sys/linux-image-*-rt-v8+_*_arm64.deb` (the
old cache location). After this change, kernel `.deb` files live in `cache/`
at the repo root. Two options:

**Option A (preferred):** `fetch-packages.sh` copies kernel `.deb` files into
`stage2/05-pistomp/files/sys/` after building, preserving the existing
`03-run.sh` install logic unchanged.

**Option B:** Bind-mount `cache/` into the Docker build container (as PLAN-3e
proposes for all packages) and update `03-run.sh` to install from the
bind-mounted path. More consistent long-term but requires `build-docker.sh`
changes.

Start with Option A — least disruption, no `03-run.sh` or `build-docker.sh`
changes needed.

---

## `build-rt-kernel-docker.sh` retirement

Once `debpkgs/linux-rpi-rt/build.sh` is working:
1. Update `CLAUDE.md` §Building — replace "Step 1: Run `./build-rt-kernel-docker.sh`"
   with "Run `./scripts/fetch-packages.sh linux-rpi-rt`" (or just
   `./scripts/fetch-packages.sh` to build all packages).
2. Delete `build-rt-kernel-docker.sh` or keep as a thin shim that calls
   `debpkgs/linux-rpi-rt/build.sh` for backward compatibility during transition.

---

## `fetch-packages.sh` registration

`fetch-packages.sh` discovers packages by scanning `debpkgs/*/build.sh`. Since
`debpkgs/linux-rpi-rt/build.sh` will exist, no explicit registration is needed
— it is picked up automatically. The existing `FORCE_REBUILD=1` mechanism works
unchanged.

---

## `.kernel-cache/` gitignore

The existing `.kernel-cache/` directory (source tarballs) should be in
`.gitignore`. Check and add if missing.

---

## Implementation order

1. Add `KERNEL_LOCALVERSION` to `config.sh` (consolidate from
   `build-rt-kernel-docker.sh`).
2. Create `debpkgs/linux-rpi-rt/build.sh` with native + Docker paths.
3. Create `debpkgs/linux-rpi-rt/README.md` noting no `debian/` tree.
4. Update `fetch-packages.sh` Option A logic: after building kernel debs,
   copy them to `stage2/05-pistomp/files/sys/`.
5. Add `.kernel-cache/` to `.gitignore`.
6. Smoke-test: `FORCE_REBUILD=1 ./scripts/fetch-packages.sh linux-rpi-rt`.
7. Retire `build-rt-kernel-docker.sh` (delete or shim).
8. Update `CLAUDE.md` build instructions.
