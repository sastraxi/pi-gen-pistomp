from abc import ABC
import subprocess
from pathlib import Path
from contextlib import contextmanager
import contextvars

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


class Component(ABC):
    name: str
    repo_url: str | None = None
    default_branch: str | None = None
    persistent_repo_path: Path | None = None

    def build_and_install(self, source_dir: Path) -> None:  # pyright: ignore[reportUnusedParameter]
        raise NotImplementedError