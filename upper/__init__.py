# Copyright 2024 Jesse Stricker.
# SPDX-License-Identifier: Apache-2.0

import shlex
import subprocess
from abc import ABC, abstractmethod
from argparse import ArgumentParser
from importlib import metadata
from pathlib import Path

from . import logger


class PackageManager(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def upgrade(self) -> bool:
        raise NotImplementedError

    def post_upgrade(self) -> None:
        return


USR_BIN_DIR = Path("/usr/bin")
SUDO_EXE = USR_BIN_DIR / "sudo"
APT_GET_EXE = USR_BIN_DIR / "apt-get"
SNAP_EXE = USR_BIN_DIR / "snap"

APT_REBOOT_REQUIRED_FILE = Path("/run/reboot-required")


class Apt(PackageManager):
    @property
    def name(self) -> str:
        return "APT"

    def upgrade(self) -> bool:
        return _exec(
            [APT_GET_EXE, "upgrade", "--update", "--assume-yes", "--verbose-versions"],
            use_sudo=True,
        )

    def post_upgrade(self) -> None:
        if not APT_REBOOT_REQUIRED_FILE.is_file():
            return

        logger.warning("A reboot is required.")


class Snap(PackageManager):
    @property
    def name(self) -> str:
        return "Snap"

    def upgrade(self) -> bool:
        return _exec([SNAP_EXE, "refresh"], use_sudo=True)


PACKAGE_MANAGERS = [Apt(), Snap()]


def main() -> int | None:
    app_meta = metadata.metadata(__package__)
    parser = ArgumentParser(prog=app_meta["Name"], description=app_meta["Summary"])
    parser.add_argument(
        "-V", "--version", action="version", version=app_meta["Version"]
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print information helpful for debugging",
    )
    args = parser.parse_args()

    if args.verbose:
        logger.set_level(logger.Level.DEBUG)

    for pm in PACKAGE_MANAGERS:
        logger.info(pm.name)
        if not pm.upgrade():
            logger.error(f"failed to upgrade {pm.name}")
            return 1

    for pm in PACKAGE_MANAGERS:
        pm.post_upgrade()

    return None


def _exec(cmd: list[str | Path], *, use_sudo: bool = False) -> bool:
    if use_sudo:
        cmd = [SUDO_EXE, "--", *cmd]

    logger.debug(lambda: f"executing: {shlex.join(str(x)for x in cmd)}")

    result = subprocess.run(cmd, check=False)
    return result.returncode == 0
