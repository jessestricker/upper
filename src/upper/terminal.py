from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Self

_ESC = "\x1b"
_CSI = _ESC + "["


def _sgr(codes: Iterable[int]) -> str:
    codes_str = ";".join(str(code) for code in codes)
    if not codes_str:
        return ""
    return _CSI + codes_str + "m"


class _Reset:
    def __repr__(self: Self) -> str:
        return "RESET"

    def __str__(self) -> str:
        return _sgr((0,))


RESET = _Reset()


class _Attribute(Enum):
    _value_: int

    def __new__(cls, value: int) -> Self:
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __repr__(self) -> str:
        return f"{type(self).__name__}.{self.name}"

    def __str__(self) -> str:
        return _sgr((self.value,))


class Foreground(_Attribute):
    DEFAULT = 39

    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37

    BRIGHT_BLACK = 90
    BRIGHT_RED = 91
    BRIGHT_GREEN = 92
    BRIGHT_YELLOW = 93
    BRIGHT_BLUE = 94
    BRIGHT_MAGENTA = 95
    BRIGHT_CYAN = 96
    BRIGHT_WHITE = 97


class Background(_Attribute):
    DEFAULT = 49

    BLACK = 40
    RED = 41
    GREEN = 42
    YELLOW = 43
    BLUE = 44
    MAGENTA = 45
    CYAN = 46
    WHITE = 47

    BRIGHT_BLACK = 100
    BRIGHT_RED = 101
    BRIGHT_GREEN = 102
    BRIGHT_YELLOW = 103
    BRIGHT_BLUE = 104
    BRIGHT_MAGENTA = 105
    BRIGHT_CYAN = 106
    BRIGHT_WHITE = 107


class Intensity(_Attribute):
    NORMAL = 22
    BOLD = 1
    FAINT = 2


class Underline(_Attribute):
    NONE = 24
    SINGLE = 4


@dataclass(frozen=True)
class Style:
    foreground: Foreground | None = None
    background: Background | None = None
    intensity: Intensity | None = None
    underlined: Underline | None = None

    def __str__(self) -> str:
        attributes = (
            self.foreground,
            self.background,
            self.intensity,
            self.underlined,
        )
        return _sgr(attr.value for attr in attributes if attr is not None)
