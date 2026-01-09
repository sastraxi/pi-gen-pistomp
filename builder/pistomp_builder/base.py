from abc import ABC
import subprocess
from pathlib import Path


# Helper to run commands
def run_cmd(
    cmd: str,
    cwd: Path | None = None,
    check: bool = True,
    shell: bool = False,
    env: dict[str, str] | None = None,
):
    print(f"Running: {cmd} (cwd={cwd})")
    _ = subprocess.run(cmd, cwd=cwd, check=check, shell=shell, env=env)


def sudo_install(src: Path, dest: Path):
    run_cmd(f"sudo install -m 644 {src} {dest}", shell=True)


class Component(ABC):
    name: str
    repo_url: str | None = None
    default_branch: str | None = None
    persistent_repo_path: Path | None = None

    def build_and_install(self, source_dir: Path) -> None:  # pyright: ignore[reportUnusedParameter]
        raise NotImplementedError
