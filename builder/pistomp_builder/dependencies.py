from pathlib import Path
import os
import subprocess
from .base import Component, run_cmd, superuser


class Jack2(Component):
    name = "jack2"
    repo_url = "https://github.com/micahvdm/jack2.git"
    services = ["jack", "mod-host", "mod-ui"]

    def build_and_install(self, source_dir: Path):
        run_cmd("./waf configure", cwd=source_dir, shell=True)
        run_cmd("./waf build", cwd=source_dir, shell=True)
        with superuser():
            run_cmd("./waf install", cwd=source_dir, shell=True)


class Hylia(Component):
    name = "hylia"
    repo_url = "https://github.com/falkTX/Hylia.git"
    services = ["mod-ui"]

    def build_and_install(self, source_dir: Path):
        # INSPIRATION.sh sets export NOOPT=true
        env = os.environ.copy()
        env["NOOPT"] = "true"
        run_cmd("make", cwd=source_dir, env=env)
        with superuser():
            run_cmd("make install", cwd=source_dir, shell=True)


class BrowsePy(Component):
    name = "browsepy"
    repo_url = "https://github.com/micahvdm/browsepy.git"

    def build_and_install(self, source_dir: Path):
        with superuser():
            run_cmd("pip3 install ./", cwd=source_dir, shell=True)


class AmidiThru(Component):
    name = "amidithru"
    repo_url = "https://github.com/BlokasLabs/amidithru.git"

    def build_and_install(self, source_dir: Path):
        # sed -i 's/CXX=g++.*/CXX=g++/' Makefile
        # run_cmd("sed -i 's/CXX=g++.*/CXX=g++/' Makefile", cwd=source_dir, shell=True)
        # Assuming we don't need sudo for editing the makefile in the source dir (owned by user)
        # If we do (e.g. root clone), run_cmd might fail if we are pistomp. 
        # But source_dir is usually prepared by the builder.
        run_cmd("sed -i 's/CXX=g++.*/CXX=g++/' Makefile", cwd=source_dir, shell=True)
        with superuser():
            run_cmd("make install", cwd=source_dir, shell=True)


class TouchOsc2Midi(Component):
    name = "touchosc2midi"
    repo_url = "https://github.com/micahvdm/touchosc2midi.git"

    def build_and_install(self, source_dir: Path):
        with superuser():
            run_cmd("pip3 install ./", cwd=source_dir, shell=True)


class ModMidiMerger(Component):
    name = "mod-midi-merger"
    repo_url = "https://github.com/micahvdm/mod-midi-merger.git"

    def build_and_install(self, source_dir: Path):
        build_dir = source_dir / "build"
        build_dir.mkdir(exist_ok=True)
        run_cmd("cmake ..", cwd=build_dir, shell=True)
        run_cmd("make", cwd=build_dir)
        with superuser():
            run_cmd("make install", cwd=build_dir, shell=True)


class ModTtyMidi(Component):
    name = "mod-ttymidi"
    repo_url = "https://github.com/moddevices/mod-ttymidi.git"

    def build_and_install(self, source_dir: Path):
        with superuser():
            run_cmd("make install", cwd=source_dir, shell=True)


class Lilv(Component):
    name = "lilv"
    # No repo_url, uses tarball
    services = ["mod-host", "mod-ui"]

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
            "./waf",
            "configure",
            "--prefix=/usr/local",
            "--static",
            "--static-progs",
            "--no-shared",
            "--no-utils",
            "--no-bash-completion",
            f"--pythondir=/usr/local/lib/python{py_ver}/dist-packages",
        ]
        # Using subprocess directly to pass env
        print(f"Running: {' '.join(cmd)} in {source_dir}")
        subprocess.run(cmd, cwd=source_dir, check=True, env=env)

        run_cmd("./waf build", cwd=source_dir, shell=True)
        with superuser():
            run_cmd("./waf install", cwd=source_dir, shell=True)