from collections import namedtuple
from dataclasses import dataclass
from enum import Enum, auto


class IconMode(Enum):
    ICONS = auto()
    LABELS = auto()
    BLANK = auto()


@dataclass(frozen=True)
class Button:
    slug: str
    display_name: str
    action: str


@dataclass(frozen=True)
class Routine:
    slug: str
    display_name: str


@dataclass(frozen=True)
class Other:
    slug: str
    display_name: str


Dispatch = namedtuple("Dispatch", ["gif", "action", "name"], defaults=[None])
