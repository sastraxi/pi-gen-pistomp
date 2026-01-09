from pathlib import Path
from typing import Union, Optional
from .executor import run_cmd

class fs:
    @staticmethod
    def exists(path: Union[Path, str]) -> bool:
        """Check if path exists (local or remote)."""
        cmd = f"test -e {path}"
        # We need check=False so we can read return code
        ret = run_cmd(cmd, check=False, shell=True)
        return ret.returncode == 0

    @staticmethod
    def mkdir(path: Union[Path, str], parents: bool = True, exist_ok: bool = True):
        """Create directory."""
        flags = []
        if parents:
            flags.append("-p")
        # exist_ok is implied by -p usually
        cmd = f"mkdir {' '.join(flags)} {path}"
        run_cmd(cmd, shell=True)

    @staticmethod
    def chown(
        path: Union[Path, str], user: str, group: Optional[str] = None, recursive: bool = False
    ):
        """Change ownership."""
        flags = "-R" if recursive else ""
        owner = f"{user}:{group}" if group else user
        cmd = f"chown {flags} {owner} {path}"
        run_cmd(cmd, shell=True)

    @staticmethod
    def install(src: Union[Path, str], dest: Union[Path, str], mode: str = "644"):
        """Install file (copy)."""
        run_cmd(f"install -m {mode} {src} {dest}", shell=True)

    @staticmethod
    def rm(path: Union[Path, str], recursive: bool = False, force: bool = False):
        """Remove file or directory."""
        flags = []
        if recursive:
            flags.append("-r")
        if force:
            flags.append("-f")
        cmd = f"rm {' '.join(flags)} {path}"
        run_cmd(cmd, shell=True)
