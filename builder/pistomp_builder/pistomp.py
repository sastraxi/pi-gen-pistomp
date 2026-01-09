from pathlib import Path
import os
import getpass
from .base import Component, run_cmd, superuser


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
        current_user = getpass.getuser()

        # --- User Space Operations ---

        # Ensure directories
        (user_home / "data/config").mkdir(parents=True, exist_ok=True)
        (user_home / "data/user-files").mkdir(
            parents=True, exist_ok=True
        )  # Usually separate clone

        # Install Config Templates
        config_dir = user_home / "data/config"

        target_config = config_dir / "default_config.yml"
        if not target_config.exists():
            run_cmd(
                f"install -m 644 {source_dir}/setup/config_templates/default_config.yml {config_dir}/",
                shell=True,
            )
        else:
            print(f"Config {target_config} exists. Skipping overwrite.")

        target_hw = config_dir / "default-hardware-descriptor.json"
        if not target_hw.exists():
            run_cmd(
                f"install -m 644 {source_dir}/setup/config_templates/default-hardware-descriptor.json {config_dir}/",
                shell=True,
            )
        else:
            print(f"Config {target_hw} exists. Skipping overwrite.")

        # Ensure data directory ownership if running as root
        # This covers config, user-files, and any other subdirs created
        if current_user != first_user:
            with superuser():
                run_cmd(f"chown -R {first_user}:{first_user} {user_home}/data", shell=True)

        # --- System Operations ---
        with superuser():
            # System Directories
            run_cmd("mkdir -p /usr/mod/scripts", shell=True)
            
            wifi_lib = Path("/usr/lib/pistomp-wifi")
            run_cmd(f"mkdir -p {wifi_lib}", shell=True)

            # Install wifi scripts
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

            # Core Services
            # mod-ala-pi-stomp and ttymidi
            run_cmd(
                f"install -m 644 {source_dir}/setup/services/mod-ala-pi-stomp.service /usr/lib/systemd/system/",
                shell=True,
            )
            run_cmd(
                f"install -m 644 {source_dir}/setup/services/ttymidi.service /usr/lib/systemd/system/",
                shell=True,
            )
            
            # Wifi Lib Permissions
            # /usr/lib is system owned, so we probably want to chown this regardless of user? 
            # Original script did chown pistomp:pistomp
            # If we are pistomp user, we might not have permission to chown if we don't own it (which we won't if we just created it with sudo)
            # So sudo chown is correct here.
            run_cmd(f"chown -R {first_user}:{first_user} {wifi_lib}", shell=True)

            # Helper scripts
            run_cmd(
                f"install -m 755 {source_dir}/setup/mod-tweaks/start_touchosc2midi.sh /usr/mod/scripts/",
                shell=True,
            )

            # Main Service Enable
            # mod-ala-pi-stomp.service is installed by Stage 2 (from files/services/), we just enable it here
            run_cmd(
                "ln -sf /usr/lib/systemd/system/mod-ala-pi-stomp.service /etc/systemd/system/multi-user.target.wants/mod-ala-pi-stomp.service",
                shell=True,
            )

            # USB Mount
            deb_path = source_dir / "setup/services/usbmount.deb"
            if deb_path.exists():
                run_cmd(f"dpkg -i {deb_path}", shell=True)

            # Permissions (ensure pi-stomp repo is owned by user)
            # Only needed if we are NOT the user (e.g. root build)
            if current_user != first_user:
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
        current_user = getpass.getuser()

        # Symlink ~/.pedalboards -> data/.pedalboards
        link = user_home / ".pedalboards"
        target = user_home / "data" / ".pedalboards"

        if not link.exists():
            run_cmd(f"ln -s {target} {link}", shell=True)

        with superuser():
            if current_user != first_user:
                run_cmd(f"chown -R {first_user}:{first_user} {target}", shell=True)
                run_cmd(f"chown -h {first_user}:{first_user} {link}", shell=True)
