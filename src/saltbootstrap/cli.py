"""
    saltbootstrap.cli
    ~~~~~~~~~~~~~~~~~

    CLI entry-point for salt-bootstrap
"""
import argparse
import logging
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import List

import blessings

import saltbootstrap.output
from saltbootstrap.exceptions import SaltBoostrapBaseException
from saltbootstrap.os import abc
from saltbootstrap.utils import platform

TMP_DIR = pathlib.Path(
    # Avoid ${TMPDIR} and gettempdir() on MacOS as they yield a base path too long
    # for unix sockets: ``error: AF_UNIX path too long``
    # Gentoo Portage prefers ebuild tests are rooted in ${TMPDIR}
    os.environ.get("TMPDIR", tempfile.gettempdir())
    if not sys.platform.startswith("darwin")
    else "/tmp"
).resolve()
DEFAULT_LOGFILE_PATH = TMP_DIR / "salt-bootstrap.log"

# Disable any buffering
os.environ["PYTHONUNBUFFERED"] = "1"

# Support colored terminal on windows
if sys.platform.startswith("win"):
    import colorama

    colorama.init()

# Initialize our terminal
term = blessings.Terminal()

# Default ALL logging to INFO level
logging.root.setLevel(logging.INFO)

log = logging.getLogger(__name__)


def main(args: List[str] = sys.argv[1:]) -> None:
    global term

    parser = argparse.ArgumentParser(
        description=f"Python application to {term.bold}Bootstrap Salt{term.normal}!"
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {saltbootstrap.__version__}",
    )
    parser.add_argument(
        "--tempdir",
        default=TMP_DIR / "salt-bootstrap",
        help=(
            "Path to the temp directory to use by salt-bootstrap. "
            f"Default: {term.bold(str(TMP_DIR / 'salt-bootstrap'))}"
        ),
    )
    output_options = parser.add_argument_group("Output Options")
    color_support_group = output_options.add_mutually_exclusive_group()
    color_support_group.add_argument(
        "-c",
        "--force-color",
        "--force-colour",
        action="store_true",
        default=False,
        help="Force colored output",
    )
    color_support_group.add_argument(
        "-C",
        "--no-color",
        "--no-colour",
        action="store_true",
        default=False,
        help="Disable colored output",
    )
    output_options.add_argument(
        "-l",
        "--log-level",
        choices=list(saltbootstrap.output.LOG_LEVELS),
        default="info",
        help=f"Define the log level to use. Default: {term.bold('info')}",
    )
    output_options.add_argument(
        "--log-file",
        type=argparse.FileType(mode="w", encoding="utf-8", errors="backslashreplace"),
        default=f"{DEFAULT_LOGFILE_PATH}",
        help=f"Path to the boostrap log file. Default {term.bold(str(DEFAULT_LOGFILE_PATH))}",
    )

    install_options = parser.add_argument_group("Install Options")
    install_options.add_argument(
        "--repo",
        default=abc.OperatingSystemGitBase.upstream_salt_repo,
        help=(
            "Git repository to use on Git based bootstraps. "
            f"Default {term.bold(abc.OperatingSystemGitBase.upstream_salt_repo)}"
        ),
    )
    install_options.add_argument(
        "--virtualenv",
        default=None,
        help=(
            f"Bootstrap salt into a virtualenv. {term.red}This will install all requirements "
            f"from PyPi{term.normal}"
        ),
    )
    install_options.add_argument(
        "--virtualenv-python",
        default=None,
        help=(
            "The path to the python binary to use when creating the virtualenv. If not defined "
            "whatever python binary is found on $PATH will be used"
        ),
    )

    parser.add_argument("install_type", default="pkg", nargs="?", metavar="INSTALL_TYPE")
    parser.add_argument("salt_version", default="latest", nargs="?", metavar="SALT_VERSION")

    # Buckle Up!
    options = parser.parse_args(args=args)

    # Patch sys.stdXXX so that any output done by this script or it's subprocesses is also
    # sent to the log file
    saltbootstrap.output.patch_stds(options.log_file)

    if options.force_color:
        # Re-Initialize our terminal to force color support
        term = blessings.Terminal(force_styling=True)
    elif options.no_color:
        # Re-Initialize our terminal to disable color support
        term = blessings.Terminal(force_styling=None)

    # Setup logging
    saltbootstrap.output.setup_logging(options.log_level, term)

    log.warning("Buckle Up!")

    # Take care of our temp directory
    if isinstance(options.tempdir, str):
        options.tempdir = pathlib.Path(options.tempdir).resolve()

    if not options.tempdir.is_dir():
        os.makedirs(str(options.tempdir))

    log.info(f"{term.bold}Temporary Directory Path{term.normal}: {options.tempdir}")
    log.info(f"{term.bold}Bootstrap log file path{term.normal}: {options.log_file.name}")

    print(options)

    try:
        distro_name, distro_version, distro_codename = platform.detect()

        log.debug("Detected Distribution Information:")
        print(f"          - Distribution: {term.bold}{distro_name}{term.normal}")
        print(f"  - Distribution Version: {term.bold}{distro_version}{term.normal}",)
        print(f" - Distribution Codename: {term.bold}{distro_codename}{term.normal}",)

        for subclass in abc.get_operating_system_implementations():
            if subclass.__name__.endswith("Git"):
                klass = subclass()
                print(klass)
                klass.clone_salt_repo(options.repo, options.tempdir / "salt", "v3000.3")
                klass.create_virtualenv(options.virtualenv, options.virtualenv_python)
    except KeyboardInterrupt:
        log.warning("KeyboardInterrupt caught. Exiting...")
        parser.exit(0)
    except subprocess.TimeoutExpired as exc:
        log.error(f"The command '{' '.join(exc.cmd)}' timmed out after %s {exc.timeout}")
        parser.exit(1)
    except subprocess.CalledProcessError as exc:
        log.error(f"The command '{' '.join(exc.cmd)}' failed with exitcode {exc.returncode}")
        parser.exit(exc.returncode)
    except SaltBoostrapBaseException as exc:
        log.error(f"{exc}")
        parser.exit(1)
    parser.exit(0)
