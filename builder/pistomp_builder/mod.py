from pathlib import Path
import os
from .base import Component, run_cmd

class ModUI(Component):
    name = "mod-ui"
    repo_url = "https://github.com/TreeFallSound/mod-ui.git"
    default_branch = "pistomp-v3" # inferred/assumed

    def build_and_install(self, source_dir: Path):
        # Build utils
        utils_dir = source_dir / "utils"
        run_cmd("make clean", cwd=utils_dir, check=False, shell=True)
        run_cmd("make", cwd=utils_dir)
        
        # Install
        # Uninstall old if exists? INSPIRATION.sh does `sudo pip3 uninstall -y mod-ui`
        run_cmd("sudo pip3 uninstall -y mod-ui", check=False, shell=True)
        run_cmd("sudo python3 setup.py install", cwd=source_dir, shell=True)
        
        # Default pedalboard
        # Determine user home
        first_user = os.environ.get("FIRST_USER_NAME", "pistomp")
        user_home = Path(f"/home/{first_user}")
        
        pedalboards_dir = user_home / "data" / ".pedalboards"
        if not pedalboards_dir.exists():
            pedalboards_dir.mkdir(parents=True, exist_ok=True)
            run_cmd(f"chown -R {first_user}:{first_user} {user_home}/data", shell=True) # Ensure permissions?
            
        default_pb = source_dir / "default.pedalboard"
        if default_pb.exists():
            run_cmd(f"cp -r {default_pb} {pedalboards_dir}/", shell=True)
            run_cmd(f"chown -R {first_user}:{first_user} {pedalboards_dir}", shell=True)

        # Tornado fix
        print("Applying tornado compatibility fix...")
        try:
            # Find tornado path
            import tornado
            tornado_path = Path(tornado.__file__).parent
            httputil = tornado_path / "httputil.py"
            if httputil.exists():
                content = httputil.read_text()
                if "collections.MutableMapping" in content and "collections.abc.MutableMapping" not in content:
                    new_content = content.replace("collections.MutableMapping", "collections.abc.MutableMapping")
                    httputil.write_text(new_content)
                    print("Applied fix to httputil.py")
        except ImportError:
            print("Tornado not found, skipping fix.")
        except Exception as e:
            print(f"Error applying tornado fix: {e}")

class ModHost(Component):
    name = "mod-host"
    repo_url = "https://github.com/micahvdm/mod-host.git"
    
    def build_and_install(self, source_dir: Path):
        run_cmd("make", cwd=source_dir)
        run_cmd("sudo make install", cwd=source_dir, shell=True)
