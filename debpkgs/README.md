# debpkgs/ — Local .deb package builds

Each subdirectory holds a `build.sh` and a `debian/` tree for building an
arm64 `.deb` from upstream source.  See `template/build.sh` for the contract.

## Status

Phase 1 (monorepo): packages are built locally via `build.sh` and cached in
`../cache/`.  No CI or release pipeline yet.

## Adding a new package

1. `mkdir debpkgs/<pkg-name>`
2. Copy `template/build.sh` and adapt it
3. Create `debian/` control files
4. Add version variables to `../config.sh`
5. Run `bash fetch-packages.sh` to build and cache
