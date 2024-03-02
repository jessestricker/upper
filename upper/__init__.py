# Copyright 2024 Jesse Stricker.
# SPDX-License-Identifier: Apache-2.0

import json
import os
import shlex
import subprocess
import sys
from abc import ABC, abstractmethod
from argparse import ArgumentParser
from importlib import metadata
from pathlib import Path
from typing import Any

from . import logger

type JsonScalar = None | bool | int | float | str
type JsonArray = list[JsonValue]
type JsonObject = dict[str, JsonValue]
type JsonValue = JsonScalar | JsonArray | JsonObject


def _parse_json(json_str: str) -> JsonValue:
    return json.loads(json_str)


class PackageManager(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def upgrade(self) -> None:
        raise NotImplementedError

    def post_upgrade(self) -> None:
        return


USR_BIN_DIR = Path("/usr/bin")
SUDO_EXE = USR_BIN_DIR / "sudo"
APT_GET_EXE = USR_BIN_DIR / "apt-get"
SNAP_EXE = USR_BIN_DIR / "snap"
NPM_EXE = USR_BIN_DIR / "npm"
PIPX_EXE = USR_BIN_DIR / "pipx"

APT_REBOOT_REQUIRED_FILE = Path("/run/reboot-required")


class APT(PackageManager):
    @property
    def name(self) -> str:
        return "APT"

    def upgrade(self) -> None:
        _exec(
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

    def upgrade(self) -> None:
        _exec([SNAP_EXE, "refresh"], use_sudo=True)


class NPM(PackageManager):
    @property
    def name(self) -> str:
        return "npm"

    def upgrade(self) -> None:
        packages = _exec(
            [NPM_EXE, "outdated", "--global", "--json"],
            capture_stdout=True,
            valid_return_codes={1},
        )
        packages = _parse_json(packages)
        if not isinstance(packages, dict):
            raise TypeError

        if not packages:
            print("All packages are up-to-date.", file=sys.stderr)
            return

        for package, versions in packages.items():
            if not isinstance(versions, dict):
                raise TypeError

            current = versions["current"]
            latest = versions["latest"]
            print(f"Upgrading {package}: {current} -> {latest}", file=sys.stderr)
            _exec(
                [
                    NPM_EXE,
                    "install",
                    "--global",
                    "--no-audit",
                    "--no-fund",
                    "--silent",
                    f"{package}@{latest}",
                ],
                use_sudo=True,
            )


class Pipx(PackageManager):
    @property
    def name(self) -> str:
        return "pipx"

    def upgrade(self) -> None:
        _exec([PIPX_EXE, "upgrade-all"], env={"USE_EMOJI": "0"})


PACKAGE_MANAGERS = [APT(), Snap(), NPM(), Pipx()]


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
        pm.upgrade()

    for pm in PACKAGE_MANAGERS:
        pm.post_upgrade()

    return None


def _exec(
    cmd: list[str | Path],
    *,
    use_sudo: bool = False,
    capture_stdout: bool = False,
    valid_return_codes: set[int] | None = None,
    env: dict[str, str] | None = None,
) -> str:
    if use_sudo:
        cmd = [SUDO_EXE, "--", *cmd]

    run_kwargs = dict[str, Any]()
    if capture_stdout:
        run_kwargs["stdout"] = subprocess.PIPE
    if env is not None:
        run_kwargs["env"] = os.environ | env

    logger.debug(lambda: f"executing: {shlex.join(str(x) for x in cmd)}")
    result = subprocess.run(cmd, check=False, encoding="UTF-8", **run_kwargs)

    if valid_return_codes is None or result.returncode not in valid_return_codes:
        result.check_returncode()

    return result.stdout if capture_stdout else ""
