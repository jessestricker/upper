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


class Apt(PackageManager):
    @property
    def name(self) -> str:
        return "APT"

    def upgrade(self) -> bool:
        return _exec(
            "/usr/bin/sudo",
            "--",
            "/usr/bin/apt-get",
            "upgrade",
            "--update",
            "--assume-yes",
            "--verbose-versions",
        )

    def post_upgrade(self) -> None:
        reboot_required_file = Path("/run/reboot-required")
        if not reboot_required_file.is_file():
            return

        logger.warning("A reboot is required.")


PACKAGE_MANAGERS = [Apt()]


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


def _exec(*cmd: str) -> bool:
    logger.debug(lambda: f"executing: {shlex.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0
