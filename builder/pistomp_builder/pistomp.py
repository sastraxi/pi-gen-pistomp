from pathlib import Path
import os
from .base import Component, run_cmd


class PiStomp(Component):
    name = "pi-stomp"
    repo_url = "https://github.com/treefallsound/pi-stomp.git"
    default_branch = "pistomp-v3"

    @property
    def persistent_repo_path(self):
        first_user = os.environ.get("FIRST_USER_NAME", "pistomp")
        return Path(f"/home/{first_user}/pi-stomp")

    def build_and_install(self, source_dir: Path):
        first_user = os.environ.get("FIRST_USER_NAME", "pistomp")
        user_home = Path(f"/home/{first_user}")

        # Ensure directories
        (user_home / "data/config").mkdir(parents=True, exist_ok=True)
        Path("/usr/mod/scripts").mkdir(parents=True, exist_ok=True)
        (user_home / "data/user-files").mkdir(
            parents=True, exist_ok=True
        )  # Usually separate clone

        # Install Config Templates
        run_cmd(
            f"install -m 644 {source_dir}/setup/config_templates/default_config.yml {user_home}/data/config/",
            shell=True,
        )
        run_cmd(
            f"install -m 644 {source_dir}/setup/config_templates/default-hardware-descriptor.json {user_home}/data/config/",
            shell=True,
        )

        # Services
        # Symlink services
        # NOTE: stage3 script does: ln -sf /usr/lib/systemd/system/mod-ala-pi-stomp.service ...
        # But where does that file come from? It's installed by this component?
        # The stage2 script installed files/services/*.service.
        # But pi-stomp repo also has services?
        # stage3/01-pistomp/01-run.sh says:
        # ln -sf /usr/lib/systemd/system/mod-ala-pi-stomp.service /etc/systemd/system/multi-user.target.wants
        # And installs wifi scripts.

        # Install wifi scripts
        wifi_lib = Path("/usr/lib/pistomp-wifi")
        wifi_lib.mkdir(parents=True, exist_ok=True)
        run_cmd(
            f"install -m 755 {source_dir}/setup/services/hotspot/usr/lib/pistomp-wifi/disable_wifi_hotspot.sh {wifi_lib}",
            shell=True,
        )
        run_cmd(
            f"install -m 755 {source_dir}/setup/services/hotspot/usr/lib/pistomp-wifi/enable_wifi_hotspot.sh {wifi_lib}",
            shell=True,
        )
        run_cmd(
            f"install -m 755 {source_dir}/setup/services/wifi_check.sh {wifi_lib}",
            shell=True,
        )

        # Wifi service
        run_cmd(
            f"install -m 644 {source_dir}/setup/services/hotspot/usr/lib/systemd/system/wifi-hotspot.service /usr/lib/systemd/system/",
            shell=True,
        )
        run_cmd(f"chown -R {first_user}:{first_user} {wifi_lib}", shell=True)

        # Helper scripts
        run_cmd(
            f"install -m 755 {source_dir}/setup/mod-tweaks/start_touchosc2midi.sh /usr/mod/scripts/",
            shell=True,
        )

        # Main Service Enable
        # mod-ala-pi-stomp.service is installed by Stage 2 (from files/services/), we just enable it here
        # mimicking: ln -sf /usr/lib/systemd/system/mod-ala-pi-stomp.service /etc/systemd/system/multi-user.target.wants
        run_cmd(
            "ln -sf /usr/lib/systemd/system/mod-ala-pi-stomp.service /etc/systemd/system/multi-user.target.wants/mod-ala-pi-stomp.service",
            shell=True,
        )

        # USB Mount
        deb_path = source_dir / "setup/services/usbmount.deb"
        if deb_path.exists():
            run_cmd(f"sudo dpkg -i {deb_path}", shell=True)

        # Permissions
        run_cmd(f"chown -R {first_user}:{first_user} {user_home}/pi-stomp", shell=True)


class PiStompPedalboards(Component):
    name = "pi-stomp-pedalboards"
    repo_url = "https://github.com/TreeFallSound/pi-stomp-pedalboards.git"

    @property
    def persistent_repo_path(self):
        first_user = os.environ.get("FIRST_USER_NAME", "pistomp")
        return Path(f"/home/{first_user}/data/.pedalboards")

    def build_and_install(self, source_dir: Path):
        first_user = os.environ.get("FIRST_USER_NAME", "pistomp")
        user_home = Path(f"/home/{first_user}")

        # Symlink ~/.pedalboards -> data/.pedalboards
        link = user_home / ".pedalboards"
        target = user_home / "data" / ".pedalboards"

        if not link.exists():
            run_cmd(f"ln -s {target} {link}", shell=True)

        run_cmd(f"chown -R {first_user}:{first_user} {target}", shell=True)
        run_cmd(f"chown -h {first_user}:{first_user} {link}", shell=True)
