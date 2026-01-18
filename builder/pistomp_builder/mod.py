from typing import final
from typing_extensions import override
from pathlib import Path
import os
import getpass
from .model import Component
from .executor import run_cmd, superuser, get_env_var
from .filesystem import fs


@final
class ModUI(Component):
    name = "mod-ui"
    url = "https://github.com/TreeFallSound/mod-ui.git"
    default_branch = "ps-1.13"
    services = ["mod-ui"]

    @override
    def build_and_install(self, source_dir: Path):
        first_user = os.environ.get("FIRST_USER_NAME", "pistomp")
        user_home = Path(f"/home/{first_user}")
        current_user = getpass.getuser()

        # Build utils
        utils_dir = source_dir / "utils"
        run_cmd("make clean", cwd=utils_dir, check=False, shell=True)
        run_cmd("make", cwd=utils_dir)

        # Reinstall
        with superuser():
            run_cmd("pip3 uninstall -y mod-ui", check=False, shell=True)
            run_cmd("python3 setup.py install", cwd=source_dir, shell=True)

        # Default pedalboard
        pedalboards_dir = user_home / "data" / ".pedalboards"
        if not fs.exists(pedalboards_dir):
            fs.mkdir(pedalboards_dir, parents=True)
            if current_user != first_user:
                with superuser():
                    run_cmd(
                        f"chown -R {first_user}:{first_user} {user_home}/data",
                        shell=True,
                    )

        default_pb = source_dir / "default.pedalboard"
        if fs.exists(default_pb):
            run_cmd(f"cp -r {default_pb} {pedalboards_dir}/", shell=True)
            if current_user != first_user:
                with superuser():
                    run_cmd(
                        f"chown -R {first_user}:{first_user} {pedalboards_dir}",
                        shell=True,
                    )

        # Tornado fix
        print("Applying tornado compatibility fix...")
        try:
            # Find tornado path on target
            # We use python3 on target to find it
            proc = run_cmd(
                [
                    "python3",
                    "-c",
                    "import tornado, os; print(os.path.dirname(tornado.__file__))",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if proc.returncode == 0 and proc.stdout.strip():
                tornado_path = Path(proc.stdout.strip())
                httputil = tornado_path / "httputil.py"

                with superuser():
                    # Use sudo sed to handle permissions.
                    run_cmd(
                        f"sed -i -e 's/collections.MutableMapping/collections.abc.MutableMapping/g' {httputil}",
                        shell=True,
                    )
                print("Applied fix to httputil.py (via sed)")
            else:
                print("Tornado not found on target, skipping fix.")

        except Exception as e:
            print(f"Error applying tornado fix: {e}")


class ModHost(Component):
    name = "mod-host"
    # url = "https://github.com/micahvdm/mod-host.git"
    url = "https://github.com/mod-audio/mod-host.git"
    services = ["mod-host", "mod-ui"]

    def build_and_install(self, source_dir: Path):
        cflags = get_env_var("CFLAGS")
        cxxflags = get_env_var("CXXFLAGS")

        env = {
            "CFLAGS": (cflags + " -mcpu=cortex-a76 -mtune=cortex-a76").strip(),
            "CXXFLAGS": (cxxflags + " -mcpu=cortex-a76 -mtune=cortex-a76").strip(),
        }

        run_cmd("make", cwd=source_dir, env=env)
        with superuser():
            run_cmd("make install", cwd=source_dir, shell=True, env=env)
