import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .model import TargetType, UnknownTargetError


@dataclass
class Target:
    """Represents a parsed deployment target."""

    type: TargetType
    value: Any  # Path for DIR, str (URL) for GIT/TARBALL, str (name) for COMPONENT
    branch: Optional[str]
    component_name: Optional[str]

    @staticmethod
    def _normalize_component_name(name: Optional[str]) -> Optional[str]:
        """Normalize inferred component names to match known components."""
        if name and "pedalboards" in name.lower():
            return "pi-stomp-pedalboards"
        return name

    @classmethod
    def parse(cls, target: str) -> "Target":
        """
        Parses target string into a Target object.
        Types: 'dir', 'git', 'tarball', 'component'
        """
        from .components import COMPONENT_MAP

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
                component_name = cls._normalize_component_name(component_name)
                return cls(TargetType.GIT, target, branch, component_name)
            else:
                # Assume tarball
                # Try to infer component name
                filename = target.split("/")[-1]
                component_name = None
                for name in COMPONENT_MAP.keys():
                    if name in filename:
                        component_name = name
                        break
                component_name = cls._normalize_component_name(component_name)
                return cls(TargetType.TARBALL, target, branch, component_name)

        # Local Directory
        if Path(target).is_dir():
            path = Path(target)
            component_name = cls._normalize_component_name(path.name)
            return cls(TargetType.DIR, path.absolute(), branch, component_name)

        # GitHub shorthand (user/repo)
        if re.match(r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$", target):
            url = f"https://github.com/{target}.git"
            component_name = target.split("/")[-1]
            component_name = cls._normalize_component_name(component_name)
            return cls(TargetType.GIT, url, branch, component_name)

        # Known Component Name
        if target in COMPONENT_MAP:
            return cls(TargetType.COMPONENT, target, branch, target)

        raise UnknownTargetError(f"Unable to parse target: {target}")
