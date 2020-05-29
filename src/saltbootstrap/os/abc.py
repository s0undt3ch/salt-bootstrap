import logging
import pathlib
import shutil
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
    git_package_name: str = "git"
    python_package_name: str = "python"

    def __post_init__(self):
        # we can't do self.slug = ... because the dataclass is frozen
        super().__setattr__("slug", f"{self.name}-{self.version}")

    def run(self, *cmdline: str, timeout: int = 60 * 5, **kwargs) -> subprocess.CompletedProcess:
        """
        Run a command against the operating system
        """
        return subprocess.run(
            cmdline, timeout=timeout, encoding="utf-8", text=True, check=True, **kwargs
        )

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
        return self._install_system_package(package)

    def _install_system_package(self, package: str):
        raise NotImplementedError

    def bootstrap_system(self):
        """
        Bootstrap Salt in the system
        """


@dataclass(frozen=True, repr=True)
class OperatingSystemGitBase(OperatingSystemBase):
    installation_type: str = "git"
    upstream_salt_repo: str = "https://github.com/saltstack/salt.git"

    def clone_salt_repo(self, repo_address, repo_path, salt_version):
        if shutil.which("git") is None:
            self.install_system_package(self.git_package_name)

        log.info(f"Cloning {repo_address} to {repo_path}")
        if not repo_path.exists():
            self.run("git", "clone", "--depth=1", repo_address, str(repo_path))

        repo_path = str(repo_path)
        if repo_address != self.upstream_salt_repo:
            log.info(f"Grabbing tags from upstream repo at {self.upstream_salt_repo}")
            self.run("git", "remote", "add", "upstream", self.upstream_salt_repo, cwd=repo_path)
            self.run("git", "fetch", "--tags", "upstream", cwd=repo_path)

        log.info(f"Checking out {salt_version} at {repo_path}")
        self.run("git", "checkout", salt_version, cwd=repo_path)

    def create_virtualenv(self, virtualenv_path, virtualenv_python=None):
        if virtualenv_python is None:
            virtualenv_python = shutil.which("python")
        if virtualenv_python is None:
            self.install_system_package(self.python_package_name)
            virtualenv_python = shutil.which("python")
        self.run(virtualenv_python, "-m", "venv", str(virtualenv_path))

    def bootstrap_system(self):
        """
        Bootstrap Salt in the system
        """

    def pip_install_salt(self, repo_path, virtualenv_path):
        virtualenv_path = pathlib.Path(virtualenv_path)
        self.run(str(virtualenv_path / "bin" / "pip"), "install", "distro")
        self.run(str(virtualenv_path / "bin" / "pip"), "install", str(repo_path))


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
