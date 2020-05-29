from dataclasses import dataclass

from saltbootstrap.os import abc


@dataclass(frozen=True, repr=True)
class CentOSBase(abc.OperatingSystemBase):

    name: str = "centos"
    display_name: str = "CentOS"
    version: str = abc.MISSING_DEFAULT


@dataclass(frozen=True, repr=True)
class CentOSGitBase(abc.OperatingSystemGitBase):

    name: str = "centos"
    display_name: str = "CentOS"
    version: str = abc.MISSING_DEFAULT


@dataclass(frozen=True, repr=True)
class CentOS7(CentOSBase):
    version: str = "7"


@dataclass(frozen=True, repr=True)
class CentOS7Git(CentOSGitBase):
    version: str = "7"


# Make sure star importing this module only returns subclasses of OperatingSystem from this module
__all__ = [
    name
    for (name, obj) in locals().items()
    if getattr(obj, "__module__", None) == __name__
    and issubclass(obj, abc.OperatingSystemBase)
    and not name.endswith("Base")
]
