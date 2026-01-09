import os
import shutil
from pathlib import Path
from typing import Optional, List
import subprocess
import shlex

# Helper to run commands
def run_cmd(cmd: str, cwd: Optional[Path] = None, check: bool = True, shell: bool = False, env: Optional[dict] = None):
    print(f"Running: {cmd} (cwd={cwd})")
    subprocess.run(cmd, cwd=cwd, check=check, shell=shell, env=env)

def sudo_install(src: Path, dest: Path):
    run_cmd(f"sudo install -m 644 {src} {dest}", shell=True)

class Component:
    name: str
    repo_url: Optional[str] = None
    default_branch: Optional[str] = None

    def build(self, source_dir: Path, install_prefix: str = "/usr/local"):
        raise NotImplementedError

    def install(self, source_dir: Path):
        raise NotImplementedError

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

class Jack2(Component):
    name = "jack2"
    repo_url = "https://github.com/micahvdm/jack2.git"

    def build_and_install(self, source_dir: Path):
        run_cmd("./waf configure", cwd=source_dir, shell=True)
        run_cmd("./waf build", cwd=source_dir, shell=True)
        run_cmd("sudo ./waf install", cwd=source_dir, shell=True)

class Hylia(Component):
    name = "hylia"
    repo_url = "https://github.com/falkTX/Hylia.git"

    def build_and_install(self, source_dir: Path):
        # INSPIRATION.sh sets export NOOPT=true
        env = os.environ.copy()
        env["NOOPT"] = "true"
        run_cmd("make", cwd=source_dir, env=env)
        run_cmd("sudo make install", cwd=source_dir, shell=True)

class BrowsePy(Component):
    name = "browsepy"
    repo_url = "https://github.com/micahvdm/browsepy.git"

    def build_and_install(self, source_dir: Path):
        run_cmd("sudo pip3 install ./", cwd=source_dir, shell=True)

class AmidiThru(Component):
    name = "amidithru"
    repo_url = "https://github.com/BlokasLabs/amidithru.git"

    def build_and_install(self, source_dir: Path):
        # sed -i 's/CXX=g++.*/CXX=g++/' Makefile
        makefile = source_dir / "Makefile"
        content = makefile.read_text()
        content = content.replace("CXX=g++", "CXX=g++") # Verify replacement pattern
        # The script says sed -i 's/CXX=g++.*/CXX=g++/' which implies replacing CXX=g++<something> with CXX=g++
        # It's probably to remove cross-compiler prefix if any, or force g++.
        # Let's just run sed
        run_cmd("sed -i 's/CXX=g++.*/CXX=g++/' Makefile", cwd=source_dir, shell=True)
        run_cmd("sudo make install", cwd=source_dir, shell=True)

class TouchOsc2Midi(Component):
    name = "touchosc2midi"
    repo_url = "https://github.com/micahvdm/touchosc2midi.git"

    def build_and_install(self, source_dir: Path):
        run_cmd("sudo pip3 install ./", cwd=source_dir, shell=True)

class ModMidiMerger(Component):
    name = "mod-midi-merger"
    repo_url = "https://github.com/micahvdm/mod-midi-merger.git"

    def build_and_install(self, source_dir: Path):
        build_dir = source_dir / "build"
        build_dir.mkdir(exist_ok=True)
        run_cmd("cmake ..", cwd=build_dir, shell=True)
        run_cmd("make", cwd=build_dir)
        run_cmd("sudo make install", cwd=build_dir, shell=True)

class ModTtyMidi(Component):
    name = "mod-ttymidi"
    repo_url = "https://github.com/moddevices/mod-ttymidi.git"

    def build_and_install(self, source_dir: Path):
        run_cmd("sudo make install", cwd=source_dir, shell=True)

class Lilv(Component):
    name = "lilv"
    # No repo_url, uses tarball
    
    def build_and_install(self, source_dir: Path):
        # Logic for lilv waf
        import sys
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        
        env = os.environ.copy()
        env["CFLAGS"] = env.get("CFLAGS", "") + " -fPIC"
        env["CXXFLAGS"] = env.get("CXXFLAGS", "") + " -fPIC"
        
        # waf configure
        # --pythondir=/usr/local/lib/python{py_ver}/dist-packages
        # We need to ensure we run waf with the right environment
        cmd = [
            "./waf", "configure", "--prefix=/usr/local", "--static", "--static-progs",
            "--no-shared", "--no-utils", "--no-bash-completion",
            f"--pythondir=/usr/local/lib/python{py_ver}/dist-packages"
        ]
        # Using subprocess directly to pass env
        print(f"Running: {' '.join(cmd)} in {source_dir}")
        subprocess.run(cmd, cwd=source_dir, check=True, env=env)
        
        run_cmd("./waf build", cwd=source_dir, shell=True)
        run_cmd("sudo ./waf install", cwd=source_dir, shell=True)

COMPONENT_MAP = {
    "mod-ui": ModUI(),
    "mod-host": ModHost(),
    "jack2": Jack2(),
    "hylia": Hylia(),
    "browsepy": BrowsePy(),
    "amidithru": AmidiThru(),
    "touchosc2midi": TouchOsc2Midi(),
    "mod-midi-merger": ModMidiMerger(),
    "mod-ttymidi": ModTtyMidi(),
    "lilv": Lilv(),
}
