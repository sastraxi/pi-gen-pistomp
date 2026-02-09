from pathlib import Path
from typing import List, Tuple
import os
import getpass
from .model import Component
from .executor import run_cmd, superuser
from .filesystem import fs


def get_user_paths() -> Tuple[str, Path, str]:
    first_user = os.environ.get("FIRST_USER_NAME", "pistomp")
    user_home = Path(f"/home/{first_user}")
    current_user = getpass.getuser()
    return first_user, user_home, current_user


def ensure_lv2_dir(user_home: Path) -> Path:
    lv2_dir = user_home / ".lv2"
    run_cmd(f"mkdir -p {lv2_dir}", shell=True)
    return lv2_dir


def fix_ownership(paths: List[Path], owner: str) -> None:
    with superuser():
        for path in paths:
            if path.exists():
                run_cmd(f"chown -R {owner}:{owner} {path}", shell=True)


def install_lv2_plugin(plugin_src: Path, plugin_name: str) -> None:
    first_user, user_home, current_user = get_user_paths()
    lv2_dir = ensure_lv2_dir(user_home)
    target = lv2_dir / plugin_name

    if target.exists():
        run_cmd(f"rm -rf {target}", shell=True)

    run_cmd(f"cp -r {plugin_src} {lv2_dir}/", shell=True)

    if current_user != first_user:
        fix_ownership([target], first_user)


def autotools_build(
    source_dir: Path, configure_args: List[str], make_args: str = "-j$(nproc)"
) -> None:
    run_cmd("autoreconf -fiv", cwd=source_dir, shell=True)
    run_cmd(["./configure"] + configure_args, cwd=source_dir, check=True)
    run_cmd(f"make {make_args}", cwd=source_dir, shell=True)


def cmake_build(
    source_dir: Path, cmake_args: List[str], make_args: str = "-j$(nproc)"
) -> Path:
    build_dir = source_dir / "build"
    fs.mkdir(build_dir)
    run_cmd(["cmake", ".."] + cmake_args, cwd=build_dir, check=True)
    run_cmd(f"make {make_args}", cwd=build_dir, shell=True)
    return build_dir


def copy_from_staging(
    staging_subdir: Path, target_dir: Path, pattern: str = "*"
) -> None:
    if not staging_subdir.exists():
        return

    for item in staging_subdir.glob(pattern):
        target_path = target_dir / item.name
        if target_path.exists():
            run_cmd(f"rm -rf {target_path}", shell=True)
        run_cmd(f"cp -r {item} {target_dir}/", shell=True)


class ZynAddSubFX(Component):
    name = "zynaddsubfx"
    url = "https://github.com/zynaddsubfx/zynaddsubfx.git"
    services = []

    def build_and_install(self, source_dir: Path):
        first_user, user_home, current_user = get_user_paths()

        run_cmd("git submodule update --init --recursive", cwd=source_dir, shell=True)

        install_dir = source_dir / "install_staging"

        cmake_args = [
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_INSTALL_PREFIX={install_dir}",
            "-DPluginLibDir=.",
            "-DGuiModule=off",
            "-DJackEnable=ON",
            "-DAlsaEnable=ON",
            "-DLashEnable=OFF",
            "-DDssiEnable=OFF",
            "-DPaEnable=OFF",
            "-DOssEnable=OFF",
            "-DCompileTests=OFF",
        ]

        build_dir = cmake_build(source_dir, cmake_args)
        run_cmd(
            "make install 2>&1 | grep -v 'bash-completion' || true",
            cwd=build_dir,
            shell=True,
        )

        lv2_dir = ensure_lv2_dir(user_home)
        copy_from_staging(install_dir / "lv2", lv2_dir, "*.lv2")

        if current_user != first_user:
            fix_ownership([lv2_dir], first_user)


class Sfizz(Component):
    name = "sfizz"
    url = "https://github.com/sfztools/sfizz-ui.git"
    services = []

    def build_and_install(self, source_dir: Path):
        cmake_args = [
            "-DCMAKE_BUILD_TYPE=Release",
            "-DPLUGIN_LV2=ON",
            "-DPLUGIN_VST3=OFF",
            "-DPLUGIN_AU=OFF",
            "-DPLUGIN_PUREDATA=OFF",
        ]

        build_dir = cmake_build(source_dir, cmake_args, make_args="-j2")

        lv2_plugin = build_dir / "sfizz.lv2"
        if lv2_plugin.exists():
            install_lv2_plugin(lv2_plugin, "sfizz.lv2")


class LiquidSFZ(Component):
    name = "liquidsfz"
    url = "https://github.com/swesterfeld/liquidsfz.git"
    default_branch = "0.3.2"
    services = []

    def build_and_install(self, source_dir: Path):
        configure_args = [
            "--prefix=/usr/local",
            "--enable-shared",
            "--disable-static",
        ]

        autotools_build(source_dir, configure_args)

        with superuser():
            run_cmd("make install", cwd=source_dir, shell=True)

        installed_lv2 = Path("/usr/local/lib/lv2/liquidsfz.lv2")
        if installed_lv2.exists():
            install_lv2_plugin(installed_lv2, "liquidsfz.lv2")
