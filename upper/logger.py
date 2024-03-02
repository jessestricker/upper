# Copyright 2024 Jesse Stricker.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import enum
import sys
from collections.abc import Callable
from enum import Enum
from typing import NamedTuple

type MessageBuilder = Callable[[], str]
type Message = str | MessageBuilder


def debug(message: Message) -> None:
    _print(Level.DEBUG, message)


def info(message: Message) -> None:
    _print(Level.INFO, message)


def warning(message: Message) -> None:
    _print(Level.WARNING, message)


def error(message: Message) -> None:
    _print(Level.ERROR, message)


class Level(Enum):
    DEBUG = enum.auto()
    INFO = enum.auto()
    WARNING = enum.auto()
    ERROR = enum.auto()


_level: Level = Level.INFO


def set_level(level: Level) -> None:
    global _level  # noqa: PLW0603
    _level = level


class _LevelInfo(NamedTuple):
    name: str
    prefix: str
    infix: str
    suffix: str


_LEVEL_INFOS = {
    Level.DEBUG: _LevelInfo("debug: ", "\033[2m", "", "\033[0m"),
    Level.INFO: _LevelInfo("", "\033[1;34m", "", "\033[0m"),
    Level.WARNING: _LevelInfo("error: ", "\033[1;33m", "\033[0m", ""),
    Level.ERROR: _LevelInfo("error: ", "\033[1;31m", "\033[0m", ""),
}


def _print(level: Level, message: Message) -> None:
    if level.value < _level.value:
        return

    level_info = _LEVEL_INFOS[level]
    if callable(message):  # message: MessageBuilder
        message = message()

    sys.stderr.write(level_info.prefix)
    sys.stderr.write("(upper) ")
    sys.stderr.write(level_info.name)
    sys.stderr.write(level_info.infix)
    sys.stderr.write(message)
    sys.stderr.write(level_info.suffix)
    sys.stderr.write("\n")
