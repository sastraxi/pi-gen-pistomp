import typer
from typing import Optional
from pathlib import Path
import os
import sys
import subprocess
import shlex
import re
from .components import COMPONENT_MAP

app = typer.Typer()

def parse_target(target: str):
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
            # e.g. lilv-0.24.12.tar.bz2 -> lilv
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
            # We need to pass the raw target string, including #branch if it was there
            # But wait, we parsed it? No, we haven't parsed it yet in the SSH block.
            # Just pass it through.
            cmd_args.append(shlex.quote(target))
        
        # If the user explicitly provided --branch, pass it too
        if branch:
            cmd_args.extend(["--branch", shlex.quote(branch)])

        remote_cmd = " ".join(cmd_args)
        ssh_cmd = f"ssh {ssh} -t '{remote_cmd}'"
        print(f"Executing on remote {ssh}: {remote_cmd}")
        # Use simple os.system or subprocess to allow interactivity if needed
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
    if component_name not in COMPONENT_MAP:
        # Try to fuzzy match or complain
        print(f"Error: Could not determine supported component for '{target}'.")
        print(f"Detected/Inferred name: {component_name}")
        print(f"Supported components: {', '.join(COMPONENT_MAP.keys())}")
        sys.exit(1)

    component = COMPONENT_MAP[component_name]
    print(f"Deploying {component.name}...")

    # 3. Fetch/Prepare Source
    import tempfile
    
    if target_type == 'dir':
        source_dir = value
        print(f"Building from local directory: {source_dir}")
        component.build_and_install(source_dir)
        
    elif target_type == 'component':
        # Default Git Repo
        if not component.repo_url:
            # Special case for Lilv if it has no repo_url (tarball only defaults)
            if component.name == "lilv":
                # Use default tarball
                url = "http://download.drobilla.net/lilv-0.24.12.tar.bz2"
                deploy(target=url, ssh=None, branch=target_branch) # Recursive call with URL
                return
            else:
                print(f"No repository URL defined for {component.name}")
                sys.exit(1)

        url = component.repo_url
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            print(f"Cloning {url} to {tmp_path}...")
            cmd = ["git", "clone", "--recursive"]
            if target_branch:
                cmd.extend(["-b", target_branch])
            elif component.default_branch:
                 cmd.extend(["-b", component.default_branch])
            
            cmd.extend([url, str(tmp_path)])
            subprocess.run(cmd, check=True)
            component.build_and_install(tmp_path)

    elif target_type == 'git':
        url = value
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            print(f"Cloning {url} to {tmp_path}...")
            cmd = ["git", "clone", "--recursive"]
            if target_branch:
                cmd.extend(["-b", target_branch])
            cmd.extend([url, str(tmp_path)])
            subprocess.run(cmd, check=True)
            component.build_and_install(tmp_path)

    elif target_type == 'tarball':
        url = value
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
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

if __name__ == "__main__":
    app()
