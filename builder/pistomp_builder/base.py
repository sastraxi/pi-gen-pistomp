import os
import subprocess
from pathlib import Path
from typing import Optional

# Helper to run commands
def run_cmd(cmd: str, cwd: Optional[Path] = None, check: bool = True, shell: bool = False, env: Optional[dict] = None):
    print(f"Running: {cmd} (cwd={cwd})")
    subprocess.run(cmd, cwd=cwd, check=check, shell=shell, env=env)

def sudo_install(src: Path, dest: Path):
    run_cmd(f"sudo install -m 644 {src} {dest}", shell=True)

class Component:
    name: str
    repo_url: Optional[str] = None
    default_branch: Optional[str] = None
    persistent_repo_path: Optional[Path] = None

    def build_and_install(self, source_dir: Path):
        raise NotImplementedError
