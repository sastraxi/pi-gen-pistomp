from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import List, Optional

class UnknownTargetError(Exception):
    """Raised when a target string cannot be parsed into a known type."""
    pass

class TargetType(str, Enum):
    DIR = "dir"
    GIT = "git"
    TARBALL = "tarball"
    COMPONENT = "component"

class Component(ABC):
    name: str
    repo_url: Optional[str] = None
    default_branch: Optional[str] = None
    persistent_repo_path: Optional[Path] = None
    services: List[str] = []

    @abstractmethod
    def build_and_install(self, source_dir: Path) -> None:
        raise NotImplementedError
