import typer
from typing import Optional, Tuple, Any, cast
from pathlib import Path
import sys
import subprocess
import re
import random
import string
import tempfile
from enum import Enum
from .components import COMPONENT_MAP
from .base import Component, manage_service, is_chroot, ssh_connection, fs, _ssh_target

app = typer.Typer()


class TargetType(str, Enum):
    DIR = "dir"
    GIT = "git"
    TARBALL = "tarball"
    COMPONENT = "component"
    UNKNOWN = "unknown"


def parse_target(target: str) -> Tuple[TargetType, Any, Optional[str], Optional[str]]:
    """
    Parses target string into (type, value, branch, component_name).
    Types: 'dir', 'git', 'tarball', 'component'
    """
    # Check for #branch
    branch = None
    if "#" in target:
        target, branch = target.split("#", 1)

    # HTTP(S) URL
    if target.startswith("http://") or target.startswith("https://"):
        if target.endswith(".git"):
            # Git URL
            # Try to infer component name from URL
            name_match = re.search(r"/([^/]+)\.git$", target)
            component_name = name_match.group(1) if name_match else None
            return TargetType.GIT, target, branch, component_name
        else:
            # Assume tarball
            # Try to infer component name
            filename = target.split("/")[-1]
            component_name = None
            for name in COMPONENT_MAP.keys():
                if name in filename:
                    component_name = name
                    break
            return TargetType.TARBALL, target, branch, component_name

    # Local Directory
    if Path(target).is_dir():
        path = Path(target)
        return TargetType.DIR, path.absolute(), branch, path.name

    # GitHub shorthand (user/repo)
    if re.match(r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$", target):
        url = f"https://github.com/{target}.git"
        component_name = target.split("/")[-1]
        return TargetType.GIT, url, branch, component_name

    # Known Component Name
    if target in COMPONENT_MAP:
        return TargetType.COMPONENT, target, branch, target

    return TargetType.UNKNOWN, target, branch, None


def prepare_git_source(
    url: str, branch: Optional[str], component: Component
) -> Tuple[Path, Optional[tempfile.TemporaryDirectory]]:
    """
    Prepares the git source.
    If component has a persistent_repo_path, uses that.
    Otherwise, clones to a temp directory.

    Returns: (path_to_repo, temp_dir_object)
    temp_dir_object is None if persistent path is used, or the TemporaryDirectory object if used.
    """
    target_path = component.persistent_repo_path

    # Check if target_path should be treated as remote?
    # fs.exists checks remote if ssh context active.
    # Note: prepare_git_source runs logic LOCALLY to orchestrate commands remotely via run_cmd/fs.

    if target_path:
        # Persistent Mode
        print(f"Using persistent repository at {target_path}")

        # We must use fs.exists() not path.exists() because target_path is remote
        if not fs.exists(target_path):
            # Clone fresh
            print(f"Cloning {url} to {target_path}...")
            # We construct the command manually because we want it to run via run_cmd (which respects SSH)
            cmd = ["git", "clone", "--recursive"]

            # Parent dir creation?
            fs.mkdir(target_path.parent)

            if branch:
                cmd.extend(["-b", branch])
            elif component.default_branch:
                cmd.extend(["-b", component.default_branch])
            cmd.extend([url, str(target_path)])

            # Using base.run_cmd explicitly
            from .base import run_cmd

            run_cmd(cmd, check=True)
            return target_path, None
        else:
            # Update Existing
            from .base import run_cmd

            # 1. Check Dirty
            # git status --porcelain
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

            # Check remotes
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
        # If remote, we need a remote temp dir.
        # fs.exists, fs.mkdir etc.
        # But tempfile.TemporaryDirectory creates local dir.
        # We need a remote temp dir.

        # Hack: use /tmp/pistomp_build_<random>
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        remote_tmp = Path(f"/tmp/pistomp_build_{suffix}")

        print(f"Cloning {url} to temporary {remote_tmp}...")
        fs.mkdir(remote_tmp)

        # We don't have a TemporaryDirectory object that cleans up remote.
        # We can implement a cleanup later or just leave it?
        # Better: create a cleanup context manager for remote

        cmd = ["git", "clone", "--recursive"]
        if branch:
            cmd.extend(["-b", branch])
        elif component.default_branch:
            cmd.extend(["-b", component.default_branch])

        cmd.extend([url, str(remote_tmp)])

        from .base import run_cmd

        run_cmd(cmd, check=True)

        # Return path and None context (caller cleans up? we should probably delete it manually)
        # For now, let's just return it.
        return remote_tmp, None


@app.command()
def deploy(
    target: Optional[str] = typer.Argument(
        None, help="Component name, directory, Git URL, or Tarball URL"
    ),
    ssh: Optional[str] = typer.Option(
        None, "--ssh", help="SSH host (e.g., pistomp@pistomp.local) to run on"
    ),
    branch: Optional[str] = typer.Option(
        None, help="Git branch to checkout (overrides target#branch)"
    ),
    restart: bool = typer.Option(
        True, help="Restart associated services after installation"
    ),
):
    """
    Deploy a component to the system (local or remote).
    """

    # Wrapper for main logic to handle SSH context
    if ssh:
        with ssh_connection(ssh):
            _deploy_logic(target, branch, restart)
    else:
        _deploy_logic(target, branch, restart)


def _deploy_logic(target: str | None, branch: str | None, restart: bool):
    # Determine if we should really restart (check chroot)
    # is_chroot uses run_cmd which is ssh-aware
    should_restart = restart and not is_chroot()
    if restart and not should_restart:
        print("Chroot detected (or systemd inactive), suppressing service restarts.")

    # 1. Determine Target Type
    if target is None:
        # CWD
        cwd = Path.cwd()
        target_type = TargetType.DIR
        value = cwd
        target_branch = None
        component_name = cwd.name
    else:
        target_type, value, target_branch, component_name = parse_target(target)

    # Override branch if provided via flag
    if branch:
        target_branch = branch

    # 2. Validate Component
    # Fallback name matching if not found
    if component_name not in COMPONENT_MAP:
        # Try to fuzzy match or complain
        print(f"Error: Could not determine supported component for '{target}'.")
        print(f"Detected/Inferred name: {component_name}")
        print(f"Supported components: {', '.join(COMPONENT_MAP.keys())}")
        sys.exit(1)

    component = COMPONENT_MAP[component_name]
    print(f"Deploying {component.name}...")

    # Stop services
    if should_restart:
        for svc in reversed(component.services):
            manage_service(svc, "stop")

    # 3. Fetch/Prepare Source
    source_dir: Optional[Path] = None
    tmp_context: Optional[tempfile.TemporaryDirectory] = None
    remote_tmp_created = False

    ssh_ctx = _ssh_target.get()
    try:
        if target_type == TargetType.DIR:
            local_source = cast(Path, value)
            print(f"Building from local directory: {local_source}")

            if ssh_ctx:
                # Sync local dir to remote temp
                import random
                import string

                suffix = "".join(
                    random.choices(string.ascii_lowercase + string.digits, k=8)
                )
                remote_source = Path(f"/tmp/pistomp_deploy_{suffix}")

                print(f"Syncing {local_source} to remote {remote_source}...")

                # Get SSH host from context... tricky to get back from run_cmd logic?
                # Actually ssh_connection sets contextvar.
                # But for rsync we need the host string.
                # We can access _ssh_target contextvar?

                host = ssh_ctx.host

                # Use rsync
                # rsync -avz --delete --exclude=.git local_source/ host:remote_source/
                # Ensure trailing slash on source to copy contents
                src_str = str(local_source).rstrip("/") + "/"
                dst_str = f"{host}:{remote_source}"

                # Create remote dir first
                fs.mkdir(remote_source)
                remote_tmp_created = True

                # We run rsync LOCALLY (not via run_cmd ssh wrapper)
                # But run_cmd wrapper handles ssh if context is set.
                # We need to bypass context for rsync command itself because rsync handles ssh.
                # Or just use subprocess directly.

                rsync_cmd = [
                    "rsync",
                    "-avz",
                    "--exclude=.git",
                    "--exclude=__pycache__",
                    "-e",
                    f"ssh -S {ssh_ctx.control_path}",  # Use the master socket!
                    src_str,
                    dst_str,
                ]
                print("Running rsync...")
                subprocess.run(rsync_cmd, check=True)

                source_dir = remote_source
            else:
                source_dir = local_source

            # Component.build_and_install implementation handles copying if needed.
            component.build_and_install(source_dir)

        elif target_type == TargetType.COMPONENT:
            # Default Git Repo
            if not component.repo_url:
                if component.name == "lilv":
                    # Special case for lilv tarball
                    url = "http://download.drobilla.net/lilv-0.24.12.tar.bz2"
                    # Recursive call? No, just handle tarball logic.
                    # Copy-paste logic from below or refactor?
                    # Let's handle it here
                    # ... (Lilv tarball logic duplicated below) ...
                    # Or better, just set target type to TARBALL and loop
                    # But we are inside logic.
                    pass  # TODO: handle recursive deploy call cleanly?
                else:
                    print(f"No repository URL defined for {component.name}")
                    sys.exit(1)

            if component.name == "lilv" and not component.repo_url:
                url = "http://download.drobilla.net/lilv-0.24.12.tar.bz2"
                # Handle tarball download on remote
                # ...
                # For simplicity, assume GIT for now mostly or simple tarball logic
                pass

            if component.repo_url:
                source_dir, tmp_context = prepare_git_source(
                    cast(str, component.repo_url), target_branch, component
                )
                component.build_and_install(source_dir)

        elif target_type == TargetType.GIT:
            url = cast(str, value)
            source_dir, tmp_context = prepare_git_source(url, target_branch, component)
            component.build_and_install(source_dir)

        elif target_type == TargetType.TARBALL:
            url = cast(str, value)

            # If ssh, download on remote.
            if ssh_ctx:
                import random
                import string

                suffix = "".join(
                    random.choices(string.ascii_lowercase + string.digits, k=8)
                )
                remote_tmp = Path(f"/tmp/pistomp_dl_{suffix}")
                fs.mkdir(remote_tmp)
                remote_tmp_created = True  # mark for cleanup?

                filename = url.split("/")[-1]
                download_path = remote_tmp / filename

                print(f"Downloading {url} on remote...")
                from .base import run_cmd

                run_cmd(["wget", "-O", str(download_path), url], check=True)

                print("Extracting...")
                run_cmd(
                    ["tar", "xf", str(download_path), "-C", str(remote_tmp)], check=True
                )

                # Find extracted dir using ls?
                # ls -d */
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
                source_dir = extracted_dirs[0]
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
                source_dir = extracted_dirs[0]

            component.build_and_install(source_dir)

        else:
            print(f"Unknown target type for {target}")
            sys.exit(1)

    finally:
        if tmp_context and hasattr(tmp_context, "cleanup"):
            tmp_context.cleanup()

        if remote_tmp_created and source_dir and ssh_ctx:
            # Cleanup remote temp?
            # maybe source_dir.parent if we created a subdir
            # fs.run_cmd(f"rm -rf {source_dir.parent}")
            pass

    # Restart services
    if should_restart:
        for svc in component.services:
            manage_service(svc, "start")


if __name__ == "__main__":
    app()
