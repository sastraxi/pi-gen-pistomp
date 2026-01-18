from pathlib import Path
from .model import Component
from .executor import run_cmd, superuser, get_env_var
from .filesystem import fs


class Jack2(Component):
    name = "jack2"
    url = "https://github.com/jackaudio/jack2.git#1.9.22"
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


class Serd(Component):
    name = "serd"
    url = "https://download.drobilla.net/serd-0.32.6.tar.xz"
    services = []

    def build_and_install(self, source_dir: Path):
        run_cmd(
            [
                "meson",
                "setup",
                "build",
                "--prefix=/usr/local",
                "--default-library=static",
                "-Dc_args=-fPIC",
                "-Dcpp_args=-fPIC",
                "-Dtests=disabled",
                "-Ddocs=disabled",
                "-Dtools=disabled",
            ],
            cwd=source_dir,
            check=True,
        )

        run_cmd("meson compile -C build", cwd=source_dir, shell=True)

        with superuser():
            run_cmd("meson install -C build", cwd=source_dir, shell=True)


class Sord(Component):
    name = "sord"
    url = "https://download.drobilla.net/sord-0.16.20.tar.xz"
    services = []

    def build_and_install(self, source_dir: Path):
        run_cmd(
            [
                "meson",
                "setup",
                "build",
                "--prefix=/usr/local",
                "--default-library=static",
                "-Dc_args=-fPIC",
                "-Dcpp_args=-fPIC",
                "-Dtests=disabled",
                "-Ddocs=disabled",
                "-Dtools=disabled",
            ],
            cwd=source_dir,
            check=True,
        )

        run_cmd("meson compile -C build", cwd=source_dir, shell=True)

        with superuser():
            run_cmd("meson install -C build", cwd=source_dir, shell=True)


class Sratom(Component):
    name = "sratom"
    url = "https://download.drobilla.net/sratom-0.6.20.tar.xz"
    services = []

    def build_and_install(self, source_dir: Path):
        run_cmd(
            [
                "meson",
                "setup",
                "build",
                "--prefix=/usr/local",
                "--default-library=static",
                "-Dc_args=-fPIC",
                "-Dcpp_args=-fPIC",
                "-Dtests=disabled",
                "-Ddocs=disabled",
            ],
            cwd=source_dir,
            check=True,
        )

        run_cmd("meson compile -C build", cwd=source_dir, shell=True)

        with superuser():
            run_cmd("meson install -C build", cwd=source_dir, shell=True)


class Zix(Component):
    name = "zix"
    url = "https://download.drobilla.net/zix-0.8.0.tar.xz"
    services = []

    def build_and_install(self, source_dir: Path):
        run_cmd(
            [
                "meson",
                "setup",
                "build",
                "--prefix=/usr/local",
                "--default-library=static",
                "-Dc_args=-fPIC",
                "-Dcpp_args=-fPIC",
                "-Dtests=disabled",
                "-Ddocs=disabled",
                "-Dbenchmarks=disabled",
            ],
            cwd=source_dir,
            check=True,
        )

        run_cmd("meson compile -C build", cwd=source_dir, shell=True)

        with superuser():
            run_cmd("meson install -C build", cwd=source_dir, shell=True)


class Sfizz(Component):
    name = "sfizz"
    url = "https://github.com/sfztools/sfizz-ui.git"
    services = []

    def build_and_install(self, source_dir: Path):
        import os
        import getpass

        first_user = os.environ.get("FIRST_USER_NAME", "pistomp")
        user_home = Path(f"/home/{first_user}")
        current_user = getpass.getuser()

        build_dir = source_dir / "build"
        fs.mkdir(build_dir)

        # Configure with cmake - build LV2 plugin only
        run_cmd(
            [
                "cmake",
                "..",
                "-DCMAKE_BUILD_TYPE=Release",
                "-DPLUGIN_LV2=ON",
                "-DPLUGIN_VST3=OFF",
                "-DPLUGIN_AU=OFF",
                "-DPLUGIN_PUREDATA=OFF",
            ],
            cwd=build_dir,
            check=True,
        )

        # Build - single threaded to avoid issues
        run_cmd("make -j2", cwd=build_dir, shell=True)

        # Install to user's .lv2 directory
        lv2_plugin = build_dir / "sfizz.lv2"
        target_lv2_dir = user_home / ".lv2"

        # Ensure .lv2 directory exists
        run_cmd(f"mkdir -p {target_lv2_dir}", shell=True)

        # Copy plugin
        run_cmd(f"cp -r {lv2_plugin} {target_lv2_dir}/", shell=True)

        # Fix ownership if needed
        if current_user != first_user:
            with superuser():
                run_cmd(
                    f"chown -R {first_user}:{first_user} {target_lv2_dir}/sfizz.lv2",
                    shell=True,
                )


class Lilv(Component):
    name = "lilv"
    url = "https://download.drobilla.net/lilv-0.24.26.tar.xz"
    services = ["mod-host", "mod-ui"]

    def build_and_install(self, source_dir: Path):
        has_waf = fs.exists(source_dir / "waf")
        has_meson = fs.exists(source_dir / "meson.build")

        if has_meson:
            self._build_with_meson(source_dir)
        elif has_waf:
            self._build_with_waf(source_dir)
        else:
            raise RuntimeError("No supported build system found")

    def _build_with_waf(self, source_dir: Path):
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
            "--no-utils",
            "--no-bash-completion",
            f"--pythondir=/usr/local/lib/python{py_ver}/dist-packages",
        ]

        run_cmd(cmd, cwd=source_dir, check=True, env=env)
        run_cmd("./waf build", cwd=source_dir, shell=True)
        with superuser():
            run_cmd("./waf install", cwd=source_dir, shell=True)

    def _build_with_meson(self, source_dir: Path):
        run_cmd(
            [
                "meson",
                "setup",
                "build",
                "--prefix=/usr/local",
                "--default-library=shared",
                "-Dc_args=-fPIC",
                "-Dcpp_args=-fPIC",
                "-Dtools=enabled",
                "-Dtests=disabled",
                "-Ddocs=disabled",
                "-Dbindings_py=enabled",
                "-Dbindings_cpp=enabled",
            ],
            cwd=source_dir,
            check=True,
        )

        run_cmd("meson compile -C build", cwd=source_dir, shell=True)

        with superuser():
            run_cmd("rm -f /usr/local/lib/liblilv-0.a", shell=True)
            run_cmd("meson install -C build", cwd=source_dir, shell=True)
