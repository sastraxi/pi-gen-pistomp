"""Analyze pre-compiled LV2 plugins to determine dynamic library version requirements.

Scans all .so files in the LV2 plugin directory and extracts:
- NEEDED shared libraries (DT_NEEDED entries)
- GNU symbol version requirements (GLIBC, GLIBCXX, GCC, CXXABI minimums)
- Imported symbols grouped by source library
- RPATH/RUNPATH entries

Outputs a JSON report and human-readable summary.
"""

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from elftools.elf.dynamic import DynamicSection
from elftools.elf.elffile import ELFFile
from elftools.elf.gnuversions import GNUVerNeedSection
from elftools.elf.sections import SymbolTableSection


@dataclass
class BinaryInfo:
    path: str
    plugin: str
    needed: list[str] = field(default_factory=list)
    version_requirements: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    imported_symbols: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    rpath: str | None = None
    runpath: str | None = None

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "plugin": self.plugin,
            "needed": self.needed,
            "version_requirements": {
                lib: sorted(versions) for lib, versions in self.version_requirements.items()
            },
            "imported_symbols_by_lib": {
                lib: syms for lib, syms in self.imported_symbols.items()
            },
            "imported_symbol_count": sum(
                len(syms) for syms in self.imported_symbols.values()
            ),
            "rpath": self.rpath,
            "runpath": self.runpath,
        }


# Libraries that are part of the base system (glibc, libstdc++, etc.)
# We track their version requirements but don't need symbol-level analysis.
SYSTEM_LIBS = {
    "libc.so.6",
    "libm.so.6",
    "libdl.so.2",
    "libpthread.so.0",
    "librt.so.1",
    "libgcc_s.so.1",
    "libstdc++.so.6",
    "ld-linux-aarch64.so.1",
}


def analyze_binary(so_path: Path, plugin_name: str) -> BinaryInfo | None:
    """Extract dynamic linking information from a single .so file."""
    info = BinaryInfo(path=str(so_path), plugin=plugin_name)

    try:
        with open(so_path, "rb") as f:
            elf = ELFFile(f)

            # Verify it's an ARM64 ELF
            if elf.header.e_machine != "EM_AARCH64":
                return None

            # Build a mapping from symbol version index -> (library, version_string)
            # so we can attribute imported symbols to their source library.
            version_map: dict[int, tuple[str, str]] = {}
            for section in elf.iter_sections():
                if isinstance(section, GNUVerNeedSection):
                    for verneed, vernaux_iter in section.iter_versions():
                        lib = verneed.name
                        for vernaux in vernaux_iter:
                            info.version_requirements[lib].add(vernaux.name)
                            version_map[vernaux["vna_other"]] = (lib, vernaux.name)

            # Extract NEEDED, RPATH, RUNPATH from dynamic section
            for section in elf.iter_sections():
                if isinstance(section, DynamicSection):
                    for tag in section.iter_tags():
                        if tag.entry.d_tag == "DT_NEEDED":
                            info.needed.append(tag.needed)
                        elif tag.entry.d_tag == "DT_RPATH":
                            info.rpath = tag.rpath
                        elif tag.entry.d_tag == "DT_RUNPATH":
                            info.runpath = tag.runpath

            # Extract imported (undefined) symbols from .dynsym
            # and try to attribute them to NEEDED libraries via GNU version info.
            gnu_version_section = None
            for section in elf.iter_sections():
                if section.header.sh_type == "SHT_GNU_versym":
                    gnu_version_section = section
                    break

            dynsym = elf.get_section_by_name(".dynsym")
            if dynsym and isinstance(dynsym, SymbolTableSection):
                for idx, symbol in enumerate(dynsym.iter_symbols()):
                    if (
                        symbol["st_shndx"] == "SHN_UNDEF"
                        and symbol.name
                        and symbol["st_info"]["bind"] != "STB_LOCAL"
                    ):
                        # Try to find which library this symbol comes from
                        # via the GNU version table
                        attributed = False
                        if gnu_version_section and idx < gnu_version_section.num_symbols():
                            ver_idx = gnu_version_section.get_symbol(idx).entry["ndx"]
                            # ver_idx can be a string enum ('VER_NDX_LOCAL',
                            # 'VER_NDX_GLOBAL') or an int. Only ints > 1 map
                            # to version entries.
                            if isinstance(ver_idx, int) and ver_idx > 1 and ver_idx in version_map:
                                lib, _version = version_map[ver_idx]
                                info.imported_symbols[lib].append(symbol.name)
                                attributed = True

                        if not attributed:
                            info.imported_symbols["<unknown>"].append(symbol.name)

    except Exception as e:
        print(f"  ERROR processing {so_path}: {e}", file=sys.stderr)
        return None

    return info


def scan_lv2_directory(lv2_dir: Path) -> list[BinaryInfo]:
    """Scan all .so files in an LV2 plugin directory."""
    results = []
    plugin_dirs = sorted(p for p in lv2_dir.iterdir() if p.is_dir())

    for plugin_dir in plugin_dirs:
        plugin_name = plugin_dir.name
        so_files = list(plugin_dir.glob("*.so"))
        if not so_files:
            continue

        for so_file in so_files:
            info = analyze_binary(so_file, plugin_name)
            if info:
                results.append(info)

    return results


def build_report(results: list[BinaryInfo]) -> dict:
    """Build an aggregate report from individual binary analysis results."""

    # Aggregate: which libraries are needed, and by how many plugins
    lib_usage: dict[str, list[str]] = defaultdict(list)
    for info in results:
        for lib in info.needed:
            if lib not in SYSTEM_LIBS:
                lib_usage[lib].append(info.plugin)

    # Aggregate: maximum version requirements across all plugins
    max_versions: dict[str, dict[str, tuple[str, str]]] = defaultdict(dict)
    # max_versions[lib][version_prefix] = (max_version, plugin_that_needs_it)
    for info in results:
        for lib, versions in info.version_requirements.items():
            for ver in versions:
                prefix = ver.split("_")[0]  # e.g., "GLIBC" from "GLIBC_2.29"
                key = f"{prefix}"
                current = max_versions[lib].get(key)
                if current is None or _version_tuple(ver) > _version_tuple(current[0]):
                    max_versions[lib][key] = (ver, info.plugin)

    # Aggregate: all imported symbols per non-system library
    all_imported: dict[str, set[str]] = defaultdict(set)
    imported_by_plugin: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for info in results:
        for lib, syms in info.imported_symbols.items():
            if lib not in SYSTEM_LIBS:
                all_imported[lib].update(syms)
                for sym in syms:
                    imported_by_plugin[lib][sym].append(info.plugin)

    # Plugins with RPATH/RUNPATH set
    rpath_plugins = [
        {"plugin": info.plugin, "rpath": info.rpath, "runpath": info.runpath}
        for info in results
        if info.rpath or info.runpath
    ]

    return {
        "summary": {
            "total_plugins_scanned": len(set(i.plugin for i in results)),
            "total_binaries_scanned": len(results),
            "unique_non_system_libs": len(lib_usage),
        },
        "non_system_library_usage": {
            lib: {"count": len(plugins), "plugins": sorted(set(plugins))}
            for lib, plugins in sorted(lib_usage.items(), key=lambda x: -len(x[1]))
        },
        "version_requirements": {
            lib: {
                prefix: {"max_version": ver, "required_by": plugin}
                for prefix, (ver, plugin) in sorted(entries.items())
            }
            for lib, entries in sorted(max_versions.items())
        },
        "imported_symbols_per_library": {
            lib: {
                "unique_symbol_count": len(syms),
                "symbols": sorted(syms),
            }
            for lib, syms in sorted(all_imported.items())
            if lib not in SYSTEM_LIBS
        },
        "rpath_runpath": rpath_plugins,
        "per_plugin": [info.to_dict() for info in results],
    }


def _version_tuple(ver: str) -> tuple[int, ...]:
    """Parse 'GLIBC_2.29' or 'GLIBCXX_3.4.26' into a comparable tuple."""
    parts = ver.split("_", 1)
    if len(parts) < 2:
        return (0,)
    try:
        return tuple(int(x) for x in parts[1].split("."))
    except ValueError:
        return (0,)


def print_summary(report: dict) -> None:
    """Print a human-readable summary of the report."""
    s = report["summary"]
    print(f"Scanned {s['total_binaries_scanned']} binaries across {s['total_plugins_scanned']} plugins")
    print(f"Found {s['unique_non_system_libs']} unique non-system library dependencies\n")

    print("=" * 70)
    print("NON-SYSTEM LIBRARY DEPENDENCIES (sorted by usage count)")
    print("=" * 70)
    for lib, info in report["non_system_library_usage"].items():
        print(f"  {lib}: {info['count']} plugins")

    print()
    print("=" * 70)
    print("SYSTEM LIBRARY VERSION REQUIREMENTS (maximums across all plugins)")
    print("=" * 70)
    for lib, entries in report["version_requirements"].items():
        for prefix, info in entries.items():
            print(f"  {lib} requires {info['max_version']} (from {info['required_by']})")

    print()
    print("=" * 70)
    print("IMPORTED SYMBOLS PER NON-SYSTEM LIBRARY")
    print("=" * 70)
    for lib, info in report["imported_symbols_per_library"].items():
        print(f"  {lib}: {info['unique_symbol_count']} unique symbols")

    if report["rpath_runpath"]:
        print()
        print("=" * 70)
        print("PLUGINS WITH RPATH/RUNPATH")
        print("=" * 70)
        for entry in report["rpath_runpath"]:
            rp = entry["rpath"] or entry["runpath"]
            print(f"  {entry['plugin']}: {rp}")


def analyze(lv2_dir: Path, output: Path | None = None) -> dict:
    """Main analysis entrypoint. Returns the report dict."""
    print(f"Scanning {lv2_dir}...")
    results = scan_lv2_directory(lv2_dir)
    print(f"Analyzed {len(results)} binaries.\n")

    report = build_report(results)
    print_summary(report)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            json.dump(report, f, indent=2, default=list)
        print(f"\nFull report written to {output}")

    return report
