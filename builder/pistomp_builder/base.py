from abc import ABC
import subprocess
from pathlib import Path
from contextlib import contextmanager
import contextvars
import os

_is_superuser = contextvars.ContextVar("is_superuser", default=False)


@contextmanager
def superuser():
    """
    Context manager to execute commands with sudo privileges.
    """
    token = _is_superuser.set(True)
    try:
        yield
    finally:
        _is_superuser.reset(token)


# Helper to run commands
def run_cmd(
    cmd: str,
    cwd: Path | None = None,
    check: bool = True,
    shell: bool = False,
    env: dict[str, str] | None = None,
):
    if _is_superuser.get():
        if not cmd.strip().lstrip().startswith("sudo"):
            cmd = f"sudo {cmd}"

    print(f"Running: {cmd} (cwd={cwd})")
    _ = subprocess.run(cmd, cwd=cwd, check=check, shell=shell, env=env)


def sudo_install(src: Path, dest: Path):
    with superuser():
        run_cmd(f"install -m 644 {src} {dest}", shell=True)


def is_chroot() -> bool:
    """
    Check if we are running in a chroot environment (or any environment where systemd is not active).
    Returns True if systemd is NOT active/detected.
    """
    try:
        # systemctl list-units returns 0 if it can talk to systemd
        subprocess.run(
            ["systemctl", "list-units", "--no-legend", "--max=0"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return False  # Systemd is running, so NOT a simple chroot (or at least systemd is functional)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return True


def manage_service(service: str, action: str):
    """
    Manage a systemd service (start, stop, restart).
    Gracefully does nothing if running in chroot/without systemd.
    """
    if is_chroot():
        print(f"Chroot/No-Systemd detected. Skipping {action} for {service}.")
        return

    print(f"{action.capitalize()}ing {service}...")
    with superuser():
        # Use check=False to suppress errors if service doesn't exist or fails
        run_cmd(f"systemctl {action} {service}", check=False, shell=True)


class Component(ABC):
    name: str
    repo_url: str | None = None
    default_branch: str | None = None
    persistent_repo_path: Path | None = None
    services: list[str] = []  # List of services to restart after install

    def build_and_install(self, source_dir: Path) -> None:  # pyright: ignore[reportUnusedParameter]
        raise NotImplementedError
