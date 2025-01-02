import os
import pprint
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from subprocess import CalledProcessError
from typing import Protocol

from upper.terminal import RESET, Foreground, Intensity, Style

__version__ = "0.1.0"


class _UpperError(Exception):
    pass


class IsSupportedCheck(Protocol):
    def __call__(self) -> bool: ...


class UpgradeStep(Protocol):
    def __call__(self) -> None: ...


@dataclass
class PackageManager:
    title: str
    is_supported_checks: list[IsSupportedCheck]
    upgrade_steps: list[UpgradeStep]

    def __post_init__(self) -> None:
        if not self.is_supported_checks:
            msg = "is_supported_checks must not be empty"
            raise ValueError(msg)

        if not self.upgrade_steps:
            msg = "upgrade_steps must not be empty"
            raise ValueError(msg)

    def is_supported(self) -> bool:
        return all(is_supported_check() for is_supported_check in self.is_supported_checks)

    def upgrade(self) -> None:
        for upgrade_step in self.upgrade_steps:
            upgrade_step()


@dataclass
class HasEnvVarCheck(IsSupportedCheck):
    name: str

    def __call__(self) -> bool:
        return os.getenv(self.name) is not None


def has_env_var(name: str) -> HasEnvVarCheck:
    return HasEnvVarCheck(name)


@dataclass
class HasFileCheck(IsSupportedCheck):
    path: Path

    def __call__(self) -> bool:
        return self.path.is_file()


def has_file(path: Path) -> HasFileCheck:
    return HasFileCheck(path)


@dataclass
class HasProgramCheck(IsSupportedCheck):
    name: str

    def __call__(self) -> bool:
        return shutil.which(self.name) is not None


def has_program(name: str) -> HasProgramCheck:
    return HasProgramCheck(name)


_SUDO_BIN = "/usr/bin/sudo"
_BASH_BIN = "/usr/bin/bash"


@dataclass
class RunCommandStep(UpgradeStep):
    args: list[str]
    use_sudo: bool
    use_bash: bool

    def __call__(self) -> None:
        command: list[str] = []
        if self.use_sudo:
            command += [_SUDO_BIN, "--"]
        if self.use_bash:
            command += [_BASH_BIN, "-i", "-c", "--", shlex.join(self.args)]
        else:
            command += self.args

        _log_debug(f"executing {command!r}")

        try:
            subprocess.run(command, stderr=subprocess.STDOUT, check=True)  # noqa: S603
        except KeyboardInterrupt as err:
            msg = "The command was interrupted by the user."
            raise _UpperError(msg) from err
        except CalledProcessError as err:
            msg = f"The command did not execute successfully. (exit code {err.returncode})"
            raise _UpperError(msg) from err


def run(*args: str | Path) -> RunCommandStep:
    return RunCommandStep(args=[str(arg) for arg in args], use_sudo=False, use_bash=False)


def run_as_root(*args: str | Path) -> RunCommandStep:
    return RunCommandStep(args=[str(arg) for arg in args], use_sudo=True, use_bash=False)


def run_in_bash(*args: str | Path) -> RunCommandStep:
    return RunCommandStep(args=[str(arg) for arg in args], use_sudo=False, use_bash=True)


_APT_BIN = Path("/usr/bin/apt")
_APT_REBOOT_REQUIRED_FILE = Path("/run/reboot-required")


@dataclass
class _AptCheckRebootRequiredStep(UpgradeStep):
    def __call__(self) -> None:
        if not _APT_REBOOT_REQUIRED_FILE.is_file():
            return

        _log_warning("A reboot is required for some system packages to become effective.")


APT = PackageManager(
    title="APT",
    is_supported_checks=[
        has_file(_APT_BIN),
    ],
    upgrade_steps=[
        run_as_root(
            _APT_BIN,
            "upgrade",
            "--update",
            "--auto-remove",
            "--purge",
            "--verbose-versions",
            "--assume-yes",
        ),
        _AptCheckRebootRequiredStep(),
    ],
)

_SNAP_BIN = Path("/usr/bin/snap")

SNAP = PackageManager(
    title="Snap",
    is_supported_checks=[
        has_file(_SNAP_BIN),
    ],
    upgrade_steps=[
        run_as_root(_SNAP_BIN, "refresh"),
    ],
)

_PIPX_BIN = Path("/usr/bin/pipx")

PIPX = PackageManager(
    title="pipx",
    is_supported_checks=[
        has_file(_PIPX_BIN),
    ],
    upgrade_steps=[
        run(_PIPX_BIN, "upgrade-all"),
    ],
)


PNPM = PackageManager(
    title="pnpm",
    is_supported_checks=[
        has_program("pnpm"),
    ],
    upgrade_steps=[
        run("pnpm", "self-update"),
        run("pnpm", "upgrade", "--global"),
    ],
)


SDKMAN = PackageManager(
    title="SDKMAN!",
    is_supported_checks=[
        has_env_var("SDKMAN_DIR"),
    ],
    upgrade_steps=[
        run_in_bash("sdk", "selfupdate"),
        run_in_bash("sdk", "update"),
        run_in_bash("sdk", "upgrade"),
    ],
)


PACKAGE_MANAGERS = [
    APT,
    SNAP,
    PIPX,
    PNPM,
    SDKMAN,
]


def upgrade() -> bool:
    _log_debug(f"package managers:\n{pprint.pformat(PACKAGE_MANAGERS)}")

    all_succeeded = True

    for pm in PACKAGE_MANAGERS:
        if not pm.is_supported():
            continue

        _log_header(pm.title)

        try:
            pm.upgrade()
        except _UpperError as err:
            _log_error(str(err))
            all_succeeded = False

    return all_succeeded


debug_logging_enabled = False


_LOG_HEADER_PREFIX = Style(
    foreground=Foreground.BRIGHT_BLUE,
    intensity=Intensity.BOLD,
)
_LOG_HEADER_TEXT = Style(
    foreground=Foreground.DEFAULT,
    intensity=Intensity.BOLD,
)
_LOG_DEBUG = Style(
    intensity=Intensity.FAINT,
)
_LOG_WARNING = Style(
    foreground=Foreground.YELLOW,
    intensity=Intensity.BOLD,
)
_LOG_ERROR = Style(
    foreground=Foreground.BRIGHT_RED,
    intensity=Intensity.BOLD,
)


def _log_header(text: str) -> None:
    print(f"{_LOG_HEADER_PREFIX}(upper) ==> {_LOG_HEADER_TEXT}{text}{RESET}")


def _log_debug(text: str) -> None:
    if debug_logging_enabled:
        print(f"{_LOG_DEBUG}(upper) debug: {text}{RESET}")


def _log_warning(text: str) -> None:
    print(f"{_LOG_WARNING}(upper) warning: {text}{RESET}")


def _log_error(text: str) -> None:
    print(f"{_LOG_ERROR}(upper) error: {text}{RESET}")
