import logging
import shutil
from dataclasses import dataclass
from dataclasses import field
from typing import List

import pygit2
from virtualenv.__main__ import run_with_catch

from saltbootstrap import subprocess
from saltbootstrap.exceptions import RequiredBinaryNotFound

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

    def clone_salt_repo(self, repo_address, repo_path, salt_version):
        log.info(f"Cloning {repo_address} to {repo_path}")
        if not repo_path.exists():
            repo = pygit2.clone_repository(repo_address, str(repo_path))
        else:
            repo = pygit2.Repository(str(repo_path))

        if repo_address != self.upstream_salt_repo:
            log.info(f"Grabbing tags from upstream repo at {self.upstream_salt_repo}")
            try:
                repo.remotes["upstream"]
            except KeyError:
                repo.remotes.create("upstream", self.upstream_salt_repo)
            repo.remotes["upstream"].fetch()

        local_ref = f"refs/heads/{salt_version}"
        remote_ref = f"refs/remotes/origin/{salt_version}"
        tag_ref = f"refs/tags/{salt_version}"
        for ref in repo.listall_references():
            if ref.startswith((tag_ref, remote_ref, local_ref)):
                break
        else:
            log.error(f"Could not find a referece to {salt_version}")
        log.info(f"Checking out {salt_version} at {repo_path}")
        repo.checkout(ref)

    def create_virtualenv(self, virtualenv_path, virtualenv_python=None):
        if virtualenv_python is None:
            virtualenv_python = shutil.which("python")
        if virtualenv_python is None:
            raise RequiredBinaryNotFound("Could not find a python binary on the system")
        run_with_catch([f"--python={virtualenv_python}", virtualenv_path])

    def bootstrap_system(self, virtualenv=None, virtualenv_python=None):
        """
        Bootstrap Salt in the system
        """


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
