from pathlib import Path
from .model import Component
from .executor import run_cmd, superuser, get_python_site_packages
from .filesystem import fs


class Jack2(Component):
    name = "jack2"
    url = "https://github.com/jackaudio/jack2.git#v1.9.22"
    services = ["jack", "mod-host", "mod-ui"]

    def build_and_install(self, source_dir: Path):
        run_cmd("./waf configure", cwd=source_dir, shell=True)
        run_cmd("./waf build", cwd=source_dir, shell=True)
        with superuser():
            run_cmd("./waf install", cwd=source_dir, shell=True)


class Hylia(Component):
    name = "hylia"
    url = "https://github.com/falkTX/Hylia.git"
    services = ["mod-ui"]

    def build_and_install(self, source_dir: Path):
        env = {"NOOPT": "true"}
        run_cmd("make", cwd=source_dir, env=env)
        with superuser():
            run_cmd("make install", cwd=source_dir, shell=True)


class BrowsePy(Component):
    name = "browsepy"
    url = "https://github.com/micahvdm/browsepy.git"

    def build_and_install(self, source_dir: Path):
        with superuser():
            run_cmd("pip3 install ./", cwd=source_dir, shell=True)


class AmidiThru(Component):
    name = "amidithru"
    url = "https://github.com/BlokasLabs/amidithru.git"

    def build_and_install(self, source_dir: Path):
        run_cmd("sed -i 's/CXX=g++.*/CXX=g++/' Makefile", cwd=source_dir, shell=True)
        with superuser():
            run_cmd("make install", cwd=source_dir, shell=True)


class TouchOsc2Midi(Component):
    name = "touchosc2midi"
    url = "https://github.com/micahvdm/touchosc2midi.git"

    def build_and_install(self, source_dir: Path):
        with superuser():
            run_cmd("pip3 install ./", cwd=source_dir, shell=True)


class ModMidiMerger(Component):
    name = "mod-midi-merger"
    url = "https://github.com/micahvdm/mod-midi-merger.git"

    def build_and_install(self, source_dir: Path):
        build_dir = source_dir / "build"
        fs.mkdir(build_dir)
        run_cmd("cmake ..", cwd=build_dir, shell=True)
        run_cmd("make", cwd=build_dir)
        with superuser():
            run_cmd("make install", cwd=build_dir, shell=True)


class ModTtyMidi(Component):
    name = "mod-ttymidi"
    url = "https://github.com/moddevices/mod-ttymidi.git"

    def build_and_install(self, source_dir: Path):
        with superuser():
            run_cmd("make install", cwd=source_dir, shell=True)


class Lilv(Component):
    """
    Builds lilv 0.24.12 with WAF for Python bindings only.

    Uses --static --no-shared to produce only static libraries (.a files)
    that don't conflict with apt's liblilv-0.so.0 in /lib/aarch64-linux-gnu/.

    The Python bindings (lilv.py) will load apt's shared library at runtime,
    which is compatible because 0.24.12 bindings work with 0.24.14 runtime.

    We remove the static library after install to ensure mod-host links
    against apt's shared library, not our static one.
    """
    name = "lilv"
    url = "https://download.drobilla.net/lilv-0.24.12.tar.bz2"
    services = ["mod-host", "mod-ui"]

    def build_and_install(self, source_dir: Path):
        py_site = get_python_site_packages()

        cmd = [
            "./waf",
            "configure",
            "--prefix=/usr/local",
            "--static",
            "--static-progs",
            "--no-shared",
            "--no-utils",
            "--no-bash-completion",
            f"--pythondir={py_site}",
        ]

        run_cmd(cmd, cwd=source_dir, check=True)
        run_cmd("./waf build", cwd=source_dir, shell=True)
        with superuser():
            run_cmd("./waf install", cwd=source_dir, shell=True)
            # Remove static library - we only need Python bindings
            # mod-host should link against apt's liblilv-0.so.0
            run_cmd("rm -f /usr/local/lib/liblilv-0.a", shell=True)
            run_cmd("rm -f /usr/local/lib/pkgconfig/lilv-0.pc", shell=True)
