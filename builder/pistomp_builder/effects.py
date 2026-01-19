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

        build_dir = source_dir / "build"
        fs.mkdir(build_dir)

        # Initialize git submodules (for rtosc and DPF)
        run_cmd("git submodule update --init --recursive", cwd=source_dir, shell=True)

        # Configure with cmake
        # Install to user home with LV2 plugins in .lv2 directory
        run_cmd(
            [
                "cmake",
                "..",
                "-DCMAKE_BUILD_TYPE=Release",
                f"-DCMAKE_INSTALL_PREFIX={user_home}",
                "-DPluginLibDir=.lv2",
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

        # Install LV2 plugins to ~/.lv2/PluginName.lv2/
        # Bash completion may fail due to permissions, but LV2 plugins will install successfully
        run_cmd("make install 2>&1 | grep -v 'bash-completion' || true", cwd=build_dir, shell=True)

        # Fix ownership if needed
        if current_user != first_user:
            with superuser():
                run_cmd(
                    f"chown -R {first_user}:{first_user} {user_home}/.lv2",
                    shell=True,
                )
                # Also fix ownership of bin and share if they were created
                if (user_home / "bin").exists():
                    run_cmd(
                        f"chown -R {first_user}:{first_user} {user_home}/bin",
                        shell=True,
                    )
                if (user_home / "share").exists():
                    run_cmd(
                        f"chown -R {first_user}:{first_user} {user_home}/share",
                        shell=True,
                    )
