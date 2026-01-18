from pathlib import Path
from .model import Component
from .executor import run_cmd, superuser
from .filesystem import fs


class ZynAddSubFX(Component):
    name = "zynaddsubfx"
    url = "https://github.com/zynaddsubfx/zynaddsubfx.git"
    services = []

    def build_and_install(self, source_dir: Path):
        import os
        import getpass

        first_user = os.environ.get("FIRST_USER_NAME", "pistomp")
        user_home = Path(f"/home/{first_user}")
        current_user = getpass.getuser()
        target_lv2_dir = user_home / ".lv2"

        build_dir = source_dir / "build"
        fs.mkdir(build_dir)

        # Initialize git submodules (for rtosc and DPF)
        run_cmd("git submodule update --init --recursive", cwd=source_dir, shell=True)

        # Configure with cmake
        # Build LV2 plugins only, disable GUI, enable JACK
        run_cmd(
            [
                "cmake",
                "..",
                "-DCMAKE_BUILD_TYPE=Release",
                "-DGuiModule=off",
                "-DJackEnable=ON",
                "-DAlsaEnable=ON",
                "-DLashEnable=OFF",
                "-DDssiEnable=OFF",
                "-DPaEnable=OFF",
                "-DOssEnable=OFF",
                "-DCompileTests=OFF",
            ],
            cwd=build_dir,
            check=True,
        )

        # Build
        run_cmd("make -j$(nproc)", cwd=build_dir, shell=True)

        # Find all built LV2 plugins
        lv2_build_dir = build_dir / "src" / "Plugin"
        lv2_plugins = []
        if lv2_build_dir.exists():
            for item in lv2_build_dir.iterdir():
                lv2_dir = item / "lv2"
                if lv2_dir.exists():
                    for plugin_dir in lv2_dir.iterdir():
                        if plugin_dir.is_dir() and plugin_dir.suffix == ".lv2":
                            lv2_plugins.append(plugin_dir)

        if not lv2_plugins:
            raise RuntimeError("No LV2 plugins found after build")

        # Ensure .lv2 directory exists
        run_cmd(f"mkdir -p {target_lv2_dir}", shell=True)

        # Remove existing plugins first, then install new ones
        for plugin in lv2_plugins:
            plugin_name = plugin.name
            existing_plugin = target_lv2_dir / plugin_name

            # Remove existing plugin if it exists
            if existing_plugin.exists():
                run_cmd(f"rm -rf {existing_plugin}", shell=True)

            # Copy new plugin
            run_cmd(f"cp -r {plugin} {target_lv2_dir}/", shell=True)

        # Fix ownership if needed
        if current_user != first_user:
            with superuser():
                for plugin in lv2_plugins:
                    plugin_name = plugin.name
                    run_cmd(
                        f"chown -R {first_user}:{first_user} {target_lv2_dir}/{plugin_name}",
                        shell=True,
                    )
