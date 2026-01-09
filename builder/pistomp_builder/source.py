import tempfile
import random
import string
import re
import sys
import subprocess
from pathlib import Path
from typing import Tuple, Optional
from .model import Component
from .executor import run_cmd, _ssh_target
from .filesystem import fs

def prepare_git_source(
    url: str, branch: Optional[str], component: Component
) -> Tuple[Path, Optional[tempfile.TemporaryDirectory]]:
    """
    Prepares the git source.
    If component has a persistent_repo_path, uses that.
    Otherwise, clones to a temp directory.
    """
    target_path = component.persistent_repo_path

    if target_path:
        # Persistent Mode
        print(f"Using persistent repository at {target_path}")

        if not fs.exists(target_path):
            # Clone fresh
            print(f"Cloning {url} to {target_path}...")
            cmd = ["git", "clone", "--recursive"]

            fs.mkdir(target_path.parent)

            if branch:
                cmd.extend(["-b", branch])
            elif component.default_branch:
                cmd.extend(["-b", component.default_branch])
            cmd.extend([url, str(target_path)])

            run_cmd(cmd, check=True)
            return target_path, None
        else:
            # Update Existing
            # 1. Check Dirty
            status = run_cmd(
                ["git", "status", "--porcelain"],
                cwd=target_path,
                capture_output=True,
                text=True,
            )
            if status.stdout.strip():
                print(f"Error: Repository at {target_path} has uncommitted changes.")
                sys.exit(1)

            # 2. Manage Remote
            remote_name = "origin"
            match = re.search(r"github\.com[:/]([^/]+)/", url)
            if match:
                remote_name = match.group(1)

            remotes_proc = run_cmd(
                ["git", "remote"], cwd=target_path, capture_output=True, text=True
            )
            remotes = remotes_proc.stdout.splitlines()

            if remote_name not in remotes:
                print(f"Adding remote {remote_name} ({url})...")
                run_cmd(
                    ["git", "remote", "add", remote_name, url],
                    cwd=target_path,
                    check=True,
                )

            # 3. Fetch
            print(f"Fetching {remote_name}...")
            run_cmd(["git", "fetch", remote_name], cwd=target_path, check=True)

            # 4. Checkout / Reset
            target_branch = branch or component.default_branch or "master"

            print(f"Checking out {target_branch} from {remote_name}...")
            run_cmd(
                [
                    "git",
                    "checkout",
                    "-B",
                    target_branch,
                    f"{remote_name}/{target_branch}",
                ],
                cwd=target_path,
                check=True,
            )
            run_cmd(
                ["git", "submodule", "update", "--init", "--recursive"],
                cwd=target_path,
                check=True,
            )

            return target_path, None

    else:
        # Temporary Mode
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        remote_tmp = Path(f"/tmp/pistomp_build_{suffix}")

        print(f"Cloning {url} to temporary {remote_tmp}...")
        fs.mkdir(remote_tmp)

        cmd = ["git", "clone", "--recursive"]
        if branch:
            cmd.extend(["-b", branch])
        elif component.default_branch:
            cmd.extend(["-b", component.default_branch])

        cmd.extend([url, str(remote_tmp)])

        run_cmd(cmd, check=True)

        return remote_tmp, None

def sync_local_source(local_source: Path, excludes: Optional[list[str]] = None) -> Tuple[Path, bool]:
    """
    Syncs local directory to remote temp directory using rsync.
    Returns (remote_path, is_temp).
    """
    ssh_ctx = _ssh_target.get()
    if ssh_ctx:
        suffix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        remote_source = Path(f"/tmp/pistomp_deploy_{suffix}")

        print(f"Syncing {local_source} to remote {remote_source}...")

        host = ssh_ctx.host

        # Ensure trailing slash on source to copy contents
        src_str = str(local_source).rstrip("/") + "/"
        dst_str = f"{host}:{remote_source}"

        # Create remote dir first
        fs.mkdir(remote_source)

        rsync_cmd = [
            "rsync",
            "-avz",
            "--exclude=.git",
            "--exclude=__pycache__",
        ]
        
        if excludes:
            for pattern in excludes:
                rsync_cmd.extend(["--exclude", pattern])

        rsync_cmd.extend([
            "-e",
            f"ssh -S {ssh_ctx.control_path}",
            src_str,
            dst_str,
        ])
        subprocess.run(rsync_cmd, check=True)

        return remote_source, True
    else:
        return local_source, False

def prepare_tarball_source(url: str) -> Tuple[Path, Optional[tempfile.TemporaryDirectory]]:
    ssh_ctx = _ssh_target.get()
    
    if ssh_ctx:
        suffix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=8)
        )
        remote_tmp = Path(f"/tmp/pistomp_dl_{suffix}")
        fs.mkdir(remote_tmp)

        filename = url.split("/")[-1]
        download_path = remote_tmp / filename

        print(f"Downloading {url} on remote...")
        run_cmd(["wget", "-O", str(download_path), url], check=True)

        print("Extracting...")
        run_cmd(
            ["tar", "xf", str(download_path), "-C", str(remote_tmp)], check=True
        )

        proc = run_cmd(
            "ls -d */",
            cwd=remote_tmp,
            capture_output=True,
            text=True,
            shell=True,
        )
        extracted_dirs = [
            remote_tmp / d.strip()
            for d in proc.stdout.splitlines()
            if d.strip().endswith("/")
        ]

        if not extracted_dirs:
            print("Failed to find extracted directory.")
            sys.exit(1)
        return extracted_dirs[0], None # We rely on logic to clean up later or just leave it for now
    else:
        tmp_context = tempfile.TemporaryDirectory()
        tmp_path = Path(tmp_context.name)
        filename = url.split("/")[-1]
        download_path = tmp_path / filename

        print(f"Downloading {url}...")
        subprocess.run(["wget", "-O", str(download_path), url], check=True)

        print("Extracting...")
        subprocess.run(
            ["tar", "xf", str(download_path), "-C", str(tmp_path)], check=True
        )

        extracted_dirs = [d for d in tmp_path.iterdir() if d.is_dir()]
        if not extracted_dirs:
            print("Failed to find extracted directory.")
            sys.exit(1)
        return extracted_dirs[0], tmp_context
