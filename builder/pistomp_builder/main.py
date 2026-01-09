import typer
from typing import Optional, Tuple
from pathlib import Path
import os
import sys
import subprocess
import shlex
import re
import tempfile
import shutil
from .components import COMPONENT_MAP
from .base import Component

app = typer.Typer()

def parse_target(target: str) -> Tuple[str, any, Optional[str], Optional[str]]:
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
            name_match = re.search(r'/([^/]+)\.git$', target)
            component_name = name_match.group(1) if name_match else None
            return 'git', target, branch, component_name
        else:
            # Assume tarball
            # Try to infer component name
            filename = target.split("/")[-1]
            component_name = None
            for name in COMPONENT_MAP.keys():
                if name in filename:
                    component_name = name
                    break
            return 'tarball', target, branch, component_name

    # Local Directory
    if Path(target).is_dir():
        path = Path(target)
        return 'dir', path.absolute(), branch, path.name

    # GitHub shorthand (user/repo)
    if re.match(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$', target):
        url = f"https://github.com/{target}.git"
        component_name = target.split("/")[-1]
        return 'git', url, branch, component_name

    # Known Component Name
    if target in COMPONENT_MAP:
        return 'component', target, branch, target

    return 'unknown', target, branch, None

def prepare_git_source(url: str, branch: Optional[str], component: Component) -> Tuple[Path, Optional[tempfile.TemporaryDirectory]]:
    """
    Prepares the git source.
    If component has a persistent_repo_path, uses that.
    Otherwise, clones to a temp directory.
    
    Returns: (path_to_repo, temp_dir_object)
    temp_dir_object is None if persistent path is used, or the TemporaryDirectory object if used.
    """
    target_path = component.persistent_repo_path
    
    if target_path:
        # Persistent Mode
        print(f"Using persistent repository at {target_path}")
        
        if not target_path.exists():
            # Clone fresh
            print(f"Cloning {url} to {target_path}...")
            cmd = ["git", "clone", "--recursive"]
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if branch:
                cmd.extend(["-b", branch])
            elif component.default_branch:
                 cmd.extend(["-b", component.default_branch])
            cmd.extend([url, str(target_path)])
            subprocess.run(cmd, check=True)
            return target_path, None
        else:
            # Update Existing
            # 1. Check Dirty
            status = subprocess.run(["git", "status", "--porcelain"], cwd=target_path, capture_output=True, text=True)
            if status.stdout.strip():
                print(f"Error: Repository at {target_path} has uncommitted changes.")
                sys.exit(1)
            
            # 2. Manage Remote
            # Derive remote name from URL org
            # e.g. https://github.com/TreeFallSound/mod-ui.git -> TreeFallSound
            remote_name = "origin" # Default
            match = re.search(r'github\.com[:/]([^/]+)/', url)
            if match:
                remote_name = match.group(1)
            
            # Check if remote exists
            remotes = subprocess.run(["git", "remote"], cwd=target_path, capture_output=True, text=True).stdout.splitlines()
            if remote_name not in remotes:
                print(f"Adding remote {remote_name} ({url})...")
                subprocess.run(["git", "remote", "add", remote_name, url], cwd=target_path, check=True)
            else:
                # Update URL just in case? Or assume it's correct.
                # Let's verify URL? For now, assume if name matches, it's fine.
                pass
            
            # 3. Fetch
            print(f"Fetching {remote_name}...")
            subprocess.run(["git", "fetch", remote_name], cwd=target_path, check=True)
            
            # 4. Checkout / Reset
            target_branch = branch or component.default_branch or "master" # Fallback
            
            print(f"Checking out {target_branch} from {remote_name}...")
            # If local branch exists, we might need to reset it.
            # safe bet: git checkout -B <branch> <remote>/<branch>
            subprocess.run(["git", "checkout", "-B", target_branch, f"{remote_name}/{target_branch}"], cwd=target_path, check=True)
            subprocess.run(["git", "submodule", "update", "--init", "--recursive"], cwd=target_path, check=True)
            
            return target_path, None

    else:
        # Temporary Mode
        tmpdir = tempfile.TemporaryDirectory()
        tmp_path = Path(tmpdir.name)
        print(f"Cloning {url} to temporary {tmp_path}...")
        cmd = ["git", "clone", "--recursive"]
        if branch:
            cmd.extend(["-b", branch])
        elif component.default_branch:
             cmd.extend(["-b", component.default_branch])
        
        cmd.extend([url, str(tmp_path)])
        subprocess.run(cmd, check=True)
        return tmp_path, tmpdir

@app.command()
def deploy(
    target: Optional[str] = typer.Argument(None, help="Component name, directory, Git URL, or Tarball URL"),
    ssh: Optional[str] = typer.Option(None, "--ssh", help="SSH host (e.g., pistomp@pistomp.local) to run on"),
    branch: Optional[str] = typer.Option(None, help="Git branch to checkout (overrides target#branch)"),
):
    """
    Deploy a component to the system (local or remote).
    """
    if ssh:
        # Construct the command to run on remote
        cmd_args = ["pistomp-builder", "deploy"]
        if target:
            cmd_args.append(shlex.quote(target))
        if branch:
            cmd_args.extend(["--branch", shlex.quote(branch)])

        remote_cmd = " ".join(cmd_args)
        ssh_cmd = f"ssh {ssh} -t '{remote_cmd}'"
        print(f"Executing on remote {ssh}: {remote_cmd}")
        ret = subprocess.call(ssh_cmd, shell=True)
        sys.exit(ret)

    # Local execution
    
    # 1. Determine Target Type
    if target is None:
        # CWD
        cwd = Path.cwd()
        target_type = 'dir'
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

    # 3. Fetch/Prepare Source
    source_dir = None
    tmp_context = None # To keep temp dir alive
    
    try:
        if target_type == 'dir':
            source_dir = value
            print(f"Building from local directory: {source_dir}")
            
            # If component has persistent path and we are deploying from it, we just update it?
            # Or if we are deploying from a separate dir to the persistent path?
            # Component.build_and_install implementation handles copying if needed.
            component.build_and_install(source_dir)
            
        elif target_type == 'component':
            # Default Git Repo
            if not component.repo_url:
                if component.name == "lilv":
                    url = "http://download.drobilla.net/lilv-0.24.12.tar.bz2"
                    deploy(target=url, ssh=None, branch=target_branch)
                    return
                else:
                    print(f"No repository URL defined for {component.name}")
                    sys.exit(1)

            source_dir, tmp_context = prepare_git_source(component.repo_url, target_branch, component)
            component.build_and_install(source_dir)

        elif target_type == 'git':
            source_dir, tmp_context = prepare_git_source(value, target_branch, component)
            component.build_and_install(source_dir)

        elif target_type == 'tarball':
            url = value
            tmp_context = tempfile.TemporaryDirectory()
            tmp_path = Path(tmp_context.name)
            filename = url.split("/")[-1]
            download_path = tmp_path / filename
            
            print(f"Downloading {url}...")
            subprocess.run(["wget", "-O", str(download_path), url], check=True)
            
            print("Extracting...")
            subprocess.run(["tar", "xf", str(download_path), "-C", str(tmp_path)], check=True)
            
            # Find extracted dir
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
        if tmp_context and hasattr(tmp_context, 'cleanup'):
            tmp_context.cleanup()

if __name__ == "__main__":
    app()
