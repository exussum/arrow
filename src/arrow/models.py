import threading
from collections import namedtuple
from dataclasses import dataclass
from pathlib import Path


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


@dataclass
class NativeCache:
    icons: dict[int, bytes]
    labels: dict[int, bytes]
    frames: dict[Path, list[bytes]]
    blank: bytes


class State:
    def __init__(self, brightness):
        self.brightness = brightness
        self.show_labels = False
        self.dim_timer = None
        self.lock = threading.Lock()


Dispatch = namedtuple("Dispatch", ["gif", "action"])
