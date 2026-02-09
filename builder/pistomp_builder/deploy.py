import sys
from pathlib import Path
from typing import Optional, cast
import tempfile

from .model import TargetType
from .target import Target
from .components import COMPONENT_MAP
from .service import is_chroot, stop_services, start_services, daemon_reload
from .source import prepare_git_source, prepare_tarball_source, sync_local_source
from .executor import _ssh_target, run_cmd


def _is_tarball_url(url: str) -> bool:
    return url.endswith(('.tar.gz', '.tar.bz2', '.tar.xz', '.tgz'))

def _get_temp_root(path: Path) -> Path:
    if path.parent.name.startswith("pistomp_"):
        return path.parent
    return path

def _cleanup_remote_temp(source_dir: Path):
    cleanup_path = _get_temp_root(source_dir)
    print(f"Cleaning up {cleanup_path}")
    try:
        run_cmd(f"rm -rf {cleanup_path}", shell=True)
    except Exception as e:
        print(f"Warning: cleanup failed - {e}")

def deploy_component(target: Optional[str], branch: Optional[str], restart: bool):
    # Determine if we should really restart (check chroot)
    should_restart = restart and not is_chroot()
    if restart and not should_restart:
        print("Chroot detected (or systemd inactive), suppressing service restarts.")

    # 1. Determine Target Type
    if target is None:
        # CWD
        cwd = Path.cwd()
        parsed_target = Target(
            type=TargetType.DIR,
            value=cwd,
            branch=None,
            component_name=cwd.name
        )
    else:
        parsed_target = Target.parse(target)

    # Override branch if provided via flag
    if branch:
        parsed_target.branch = branch

    # 2. Validate Component
    if parsed_target.component_name not in COMPONENT_MAP:
        print(f"Error: Could not determine supported component for '{target}'.")
        print(f"Detected/Inferred name: {parsed_target.component_name}")
        print(f"Supported components: {', '.join(COMPONENT_MAP.keys())}")
        sys.exit(1)

    component = COMPONENT_MAP[parsed_target.component_name]
    print(f"Deploying {component.name}...")

    # Stop services
    if should_restart:
        stop_services(component)

    # 3. Fetch/Prepare Source
    source_dir: Optional[Path] = None
    tmp_context: Optional[tempfile.TemporaryDirectory] = None
    is_remote_temp = False

    try:
        if parsed_target.type == TargetType.DIR:
            local_source = cast(Path, parsed_target.value)
            print(f"Building from local directory: {local_source}")

            excludes = []
            if component.name == "pi-stomp":
                excludes.append("setup/sys")
            elif component.name == "pi-stomp-pedalboards":
                # Exclude files that aren't pedalboards
                excludes.extend(["*.sh", "*.md", "LICENSE"])

            # Include .git folder for pedalboards so they can commit from pi-stomp
            include_git = component.name == "pi-stomp-pedalboards"

            source_dir, is_remote_temp = sync_local_source(local_source, excludes=excludes, include_git=include_git)

            component.build_and_install(source_dir)

        elif parsed_target.type == TargetType.COMPONENT:
            if not component.url:
                print(f"No URL defined for {component.name}")
                sys.exit(1)

            url = cast(str, component.url)

            # Parse URL to extract branch/tag if present (e.g., "url#tag")
            url_branch = None
            if "#" in url and not _is_tarball_url(url):
                url, url_branch = url.split("#", 1)

            # Use branch from CLI flag, else from URL, else from component default
            effective_branch = parsed_target.branch or url_branch

            if _is_tarball_url(url):
                source_dir, tmp_context = prepare_tarball_source(url)
                if tmp_context is None and _ssh_target.get():
                    is_remote_temp = True
            else:
                source_dir, tmp_context = prepare_git_source(url, effective_branch, component)
                if tmp_context is None and not component.persistent_repo_path and _ssh_target.get():
                    is_remote_temp = True

            component.build_and_install(source_dir)

        elif parsed_target.type == TargetType.GIT:
            url = cast(str, parsed_target.value)
            source_dir, tmp_context = prepare_git_source(url, parsed_target.branch, component)
            if tmp_context is None and not component.persistent_repo_path and _ssh_target.get():
                 is_remote_temp = True
            component.build_and_install(source_dir)

        elif parsed_target.type == TargetType.TARBALL:
            url = cast(str, parsed_target.value)
            source_dir, tmp_context = prepare_tarball_source(url)
            if tmp_context is None and _ssh_target.get():
                 is_remote_temp = True
            component.build_and_install(source_dir)

        else:
            print(f"Unknown target type for {target}")
            sys.exit(1)

    finally:
        if tmp_context:
            tmp_context.cleanup()
        if is_remote_temp and source_dir:
            _cleanup_remote_temp(source_dir)

    # Restart services
    if should_restart:
        daemon_reload()
        start_services(component)
