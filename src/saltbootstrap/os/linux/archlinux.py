import logging
import pathlib
import shutil
from dataclasses import dataclass

from saltbootstrap.os import abc

log = logging.getLogger(__name__)


class CommonFunctionalityMixin:
    def _check_keys(self):
        gnupg_keys_path = pathlib.Path("/etc/pacman.d/gnupg")
        if not gnupg_keys_path.exists():
            self.run("pacman-key", "--init")
            self.run("pacman-key", "--populate", "archlinux")

    def upgrade_system(self):
        if self._system_upgraded:
            return
        log.warning("Upgrading System")
        # Pacman does not resolve dependencies on outdated versions
        # They always need to be updated
        self._check_keys()
        self.run("pacman", "-Syy", "--noconfirm")
        self.run("pacman", "-S", "--noconfirm", "--needed", "archlinux-keyring")
        self.run("pacman", "-Su", "--noconfirm", "--needed", "pacman")
        pacman_db_upgrade_path = shutil.which("pacman-db-upgrade")
        if pacman_db_upgrade_path:
            self.run(pacman_db_upgrade_path)
        self._system_upgraded = True

    def update_package_database(self):
        try:
            self._package_db_updated
        except AttributeError:
            self.run("pacman", "-Syy")
            super().__setattr__("_package_db_updated", True)

    def _install_system_package(self, package: str):
        self.update_package_database()
        return self.run("pacman", "-S", "--noconfirm", "--needed", package)  # type: ignore[attr-defined]


# @dataclass(frozen=True, repr=True)
# class ArchLinux(abc.OperatingSystem, CommonFunctionalityMixin):
#
#    name: str = "arch"
#    display_name: str = "Arch Linux"
#    version: str = "rolling"


@dataclass(frozen=True, repr=True)
class ArchLinuxGit(CommonFunctionalityMixin, abc.OperatingSystemGitBase):

    name: str = "arch"
    display_name: str = "Arch Linux"
    version: str = "rolling"


# Make sure star importing this module only returns subclasses of OperatingSystem from this module
__all__ = [
    name
    for (name, obj) in locals().items()
    if getattr(obj, "__module__", None) == __name__
    and issubclass(obj, abc.OperatingSystemBase)
    and not name.endswith(("Base", "Mixin"))
]
