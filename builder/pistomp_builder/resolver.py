import re
from pathlib import Path
from typing import Tuple, Any, Optional
from .model import TargetType
from .components import COMPONENT_MAP

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
