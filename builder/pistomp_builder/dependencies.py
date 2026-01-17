from pathlib import Path
from .model import Component
from .executor import run_cmd, superuser, get_env_var
from .filesystem import fs


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
        env = {"NOOPT": "true"}
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
        fs.mkdir(build_dir)
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


class Serd(Component):
    name = "serd"
    # No repo_url, uses tarball
    services = []

    def build_and_install(self, source_dir: Path):
        # Serd uses meson
        cflags = get_env_var("CFLAGS")
        cxxflags = get_env_var("CXXFLAGS")

        env = {
            "CFLAGS": (cflags + " -fPIC").strip(),
            "CXXFLAGS": (cxxflags + " -fPIC").strip(),
        }

        # Setup
        run_cmd(
            [
                "meson", "setup", "build",
                "--prefix=/usr/local",
                "--default-library=static",
                "-Dtests=disabled",
                "-Ddocs=disabled",
                "-Dtools=disabled",
            ],
            cwd=source_dir,
            check=True,
            env=env,
        )

        # Compile
        run_cmd("meson compile -C build", cwd=source_dir, shell=True)

        # Install
        with superuser():
            run_cmd("meson install -C build", cwd=source_dir, shell=True)


class Sord(Component):
    name = "sord"
    # No repo_url, uses tarball
    services = []

    def build_and_install(self, source_dir: Path):
        # Sord uses meson
        cflags = get_env_var("CFLAGS")
        cxxflags = get_env_var("CXXFLAGS")

        env = {
            "CFLAGS": (cflags + " -fPIC").strip(),
            "CXXFLAGS": (cxxflags + " -fPIC").strip(),
        }

        # Setup
        run_cmd(
            [
                "meson", "setup", "build",
                "--prefix=/usr/local",
                "--default-library=static",
                "-Dtests=disabled",
                "-Ddocs=disabled",
                "-Dtools=disabled",
            ],
            cwd=source_dir,
            check=True,
            env=env,
        )

        # Compile
        run_cmd("meson compile -C build", cwd=source_dir, shell=True)

        # Install
        with superuser():
            run_cmd("meson install -C build", cwd=source_dir, shell=True)


class Zix(Component):
    name = "zix"
    # No repo_url, uses tarball
    services = []  # No services depend directly on zix

    def build_and_install(self, source_dir: Path):
        # Zix uses meson
        cflags = get_env_var("CFLAGS")
        cxxflags = get_env_var("CXXFLAGS")

        env = {
            "CFLAGS": (cflags + " -fPIC").strip(),
            "CXXFLAGS": (cxxflags + " -fPIC").strip(),
        }

        # Setup - minimal build
        run_cmd(
            [
                "meson", "setup", "build",
                "--prefix=/usr/local",
                "--default-library=static",
                "-Dtests=disabled",
                "-Ddocs=disabled",
                "-Dbenchmarks=disabled",
            ],
            cwd=source_dir,
            check=True,
            env=env,
        )

        # Compile
        run_cmd("meson compile -C build", cwd=source_dir, shell=True)

        # Install
        with superuser():
            run_cmd("meson install -C build", cwd=source_dir, shell=True)


class Lilv(Component):
    name = "lilv"
    # No repo_url, uses tarball
    services = ["mod-host", "mod-ui"]

    def build_and_install(self, source_dir: Path):
        # Detect build system (waf or meson)
        has_waf = fs.exists(source_dir / "waf")
        has_meson = fs.exists(source_dir / "meson.build")

        if has_meson:
            self._build_with_meson(source_dir)
        elif has_waf:
            self._build_with_waf(source_dir)
        else:
            raise RuntimeError("No supported build system (waf or meson) found")

    def _build_with_waf(self, source_dir: Path):
        # Determine Python version on TARGET
        res = run_cmd(
            [
                "python3",
                "-c",
                'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")',
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        py_ver = res.stdout.strip()

        cflags = get_env_var("CFLAGS")
        cxxflags = get_env_var("CXXFLAGS")

        env = {
            "CFLAGS": (cflags + " -fPIC").strip(),
            "CXXFLAGS": (cxxflags + " -fPIC").strip(),
        }

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

        run_cmd(cmd, cwd=source_dir, check=True, env=env)
        run_cmd("./waf build", cwd=source_dir, shell=True)
        with superuser():
            run_cmd("./waf install", cwd=source_dir, shell=True)

    def _build_with_meson(self, source_dir: Path):
        # Based on INSTALL.md from lilv 0.26.x
        cflags = get_env_var("CFLAGS")
        cxxflags = get_env_var("CXXFLAGS")

        env = {
            "CFLAGS": (cflags + " -fPIC").strip(),
            "CXXFLAGS": (cxxflags + " -fPIC").strip(),
        }

        # Setup - minimal build without tools, tests, docs, bindings
        run_cmd(
            [
                "meson", "setup", "build",
                "--prefix=/usr/local",
                "--default-library=static",
                "-Dtools=disabled",
                "-Dtests=disabled",
                "-Ddocs=disabled",
                "-Dbindings_py=disabled",
                "-Dbindings_cpp=disabled",
            ],
            cwd=source_dir,
            check=True,
            env=env,
        )

        # Compile
        run_cmd("meson compile -C build", cwd=source_dir, shell=True)

        # Install
        with superuser():
            run_cmd("meson install -C build", cwd=source_dir, shell=True)
