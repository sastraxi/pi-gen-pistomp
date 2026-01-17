import sys
from pathlib import Path
from typing import Optional, cast
import tempfile

from .model import TargetType
from .target import Target
from .components import COMPONENT_MAP
from .service import is_chroot, stop_services, start_services, daemon_reload
from .source import prepare_git_source, prepare_tarball_source, sync_local_source
from .executor import _ssh_target

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

            source_dir, is_remote_temp = sync_local_source(local_source, excludes=excludes)

            component.build_and_install(source_dir)

        elif parsed_target.type == TargetType.COMPONENT:
            # Default Git Repo
            if not component.repo_url:
                if component.name == "lilv":
                     # Special case for lilv tarball
                     # TODO: Ideally Component should have a method to get source or properties defining source type
                     # For now, hardcoding lilv fallback url if repo_url is missing but we know it's lilv
                     url = "http://download.drobilla.net/lilv-0.24.12.tar.bz2"
                     source_dir, tmp_context = prepare_tarball_source(url)
                     # For remote tarball, tmp_context is None, but we might want to track it
                     if _ssh_target.get():
                         is_remote_temp = True
                     component.build_and_install(source_dir)
                else:
                    print(f"No repository URL defined for {component.name}")
                    sys.exit(1)
            else:
                source_dir, tmp_context = prepare_git_source(
                    cast(str, component.repo_url), parsed_target.branch, component
                )
                if tmp_context is None and not component.persistent_repo_path and _ssh_target.get():
                     # Ephemeral git clone on remote
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
            # Simple cleanup for remote temps if we created them
            # We assume if it's remote temp, we can delete the parent or the dir
            # source.py creates /tmp/pistomp_*
            # If source_dir is inside that, we should delete the root of that temp
            # This is a bit loose.
            pass

    # Restart services
    if should_restart:
        daemon_reload()
        start_services(component)
