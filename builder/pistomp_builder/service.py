import subprocess
from .executor import run_cmd, superuser
from .model import Component

def is_chroot() -> bool:
    """
    Check if systemd is active (not in chroot).
    """
    try:
        run_cmd(
            "systemctl list-units --no-legend | head -n 1",
            check=True,
            shell=True,
            capture_output=True,
        )
        return False
    except subprocess.CalledProcessError:
        return True

def manage_service(service: str, action: str):
    """
    Manage a systemd service (start, stop, restart).
    """
    if is_chroot():
        print(f"Chroot/No-Systemd detected. Skipping {action} for {service}.")
        return

    print(f"{action.capitalize()}ing {service}...")
    with superuser():
        run_cmd(f"systemctl {action} {service}", check=False, shell=True)

def stop_services(component: Component):
    if not component.services:
        return
    for svc in reversed(component.services):
        manage_service(svc, "stop")

def start_services(component: Component):
    if not component.services:
        return
    for svc in component.services:
        manage_service(svc, "start")
