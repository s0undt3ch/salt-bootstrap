import logging
from dataclasses import dataclass
from dataclasses import field
from typing import List

from saltbootstrap import subprocess

MISSING_DEFAULT = "missing-default-value"

log = logging.getLogger(__name__)


@dataclass(frozen=True, repr=True)
class OperatingSystemBase:
    slug: str = field(init=False)
    name: str
    display_name: str
    version: str
    salt_version: str = "latest"
    installation_type: str = "pkg"

    def __post_init__(self):
        # we can't do self.slug = ... because the dataclass is frozen
        super().__setattr__("slug", f"{self.name}-{self.version}")

    def run(self, *cmdline: str, timeout: int = 60 * 5) -> subprocess.CompletedProcess:
        """
        Run a command against the operating system
        """
        return subprocess.run(cmdline, timeout=timeout, encoding="utf-8", text=True, check=True)

    def get_system_dependencies(self) -> List[str]:
        """
        Returns a list of strings where each string will be the name of a
        system package to install
        """
        raise NotImplementedError

    def install_system_package(self, package: str):
        """
        Install the system package
        """

    def bootstrap_system(self):
        """
        Bootstrap Salt in the system
        """


@dataclass(frozen=True, repr=True)
class OperatingSystemGitBase(OperatingSystemBase):
    installation_type: str = "git"
    upstream_salt_repo: str = "https://github.com/saltstack/salt.git"

    def clone_salt_repo(self):
        pass


def _all_subclasses(cls):
    subclasses = set()
    for subclass in cls.__subclasses__():
        if not subclass.__name__.endswith(("Base", "Mixin")):
            subclasses.add(subclass)
        subclasses.update(_all_subclasses(subclass))
    return subclasses


def get_operating_system_implementations():
    return _all_subclasses(OperatingSystemBase)


__all__ = ["OperatingSystemBase", "OperatingSystemGitBase"]
