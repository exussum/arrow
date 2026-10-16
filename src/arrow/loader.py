import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import command_cfg
from command_cfg import ConfigError, array, scalar

from arrow.models import Button, Other, Routine

CONFIG_PATH = Path(__file__).resolve().parent / "config.arrow"

ACTIONS = ("on", "off", "follow")
FILTERS = ("dim", "invert")
LAYOUTS = ("single", "pair", "caption", "marked")

GRAMMAR = """
setting <key> <value>
badge <action> <icon>
room <slug> <name> <icon>
routine single <slug> <name> <icon> [--orc-id=<id>]
routine pair <slug> <name> <icon> <icon2> [--orc-id=<id>]
routine caption <slug> <name> <icon> <text> [--orc-id=<id>]
routine marked <slug> <name> <icon> <badge> [--orc-id=<id>]
other <slug> <name> <icon>
button <slug> [<action>] <key>
"""


@dataclass(frozen=True)
class Settings:
    orc_base_url: str
    presence_name: str
    http_timeout: int = 60
    dim_delay_seconds: int = 15
    active_brightness: int = 100
    dim_brightness: int = 0
    delay_notice_seconds: int = 5

    INTS = ("http_timeout", "dim_delay_seconds", "active_brightness", "dim_brightness", "delay_notice_seconds")


@dataclass(frozen=True)
class Icon:
    name: str
    filter: str | None = None

    @classmethod
    def parse(cls, spec: str) -> "Icon":
        name, _, flt = spec.partition(":")
        if flt and flt not in FILTERS:
            raise ConfigError(f"unknown icon filter {flt!r}: expected one of {FILTERS}")
        return cls(name, flt or None)

    @property
    def char(self) -> str:
        try:
            return unicodedata.lookup(self.name.replace("-", " ").upper())
        except KeyError:
            raise ConfigError(f"unknown icon name {self.name!r}") from None


@dataclass(frozen=True)
class Art:
    icons: tuple[Icon, ...]
    text: str | None = None
    badge: Icon | None = None


class BadgeRow(NamedTuple):
    action: str
    icon: str


class RoomRow(NamedTuple):
    slug: str
    name: str
    icon: str


class RoutineRow(NamedTuple):
    slug: str
    name: str
    icon: str
    single: bool = False
    pair: bool = False
    caption: bool = False
    marked: bool = False
    icon2: str | None = None
    text: str | None = None
    badge: str | None = None
    orc_id: str | None = None

    @property
    def layout(self) -> str:
        return next(name for name in LAYOUTS if getattr(self, name))


class OtherRow(NamedTuple):
    slug: str
    name: str
    icon: str


class ButtonRow(NamedTuple):
    slug: str
    key: int
    action: str | None = None


class Keys(NamedTuple):
    buttons: dict[int, Button]
    routines: dict[int, Routine]
    others: dict[int, Other]


class Parsed(NamedTuple):
    settings: Settings
    badges: dict[str, Icon]
    buttons: dict[int, Button]
    routines: dict[int, Routine]
    others: dict[int, Other]
    art: dict[str, Art]


def parse(text: str) -> Parsed:
    objects = command_cfg.load(
        text,
        GRAMMAR,
        {
            "setting": scalar(Settings, types=dict.fromkeys(Settings.INTS, _as_int)),
            "badge": array(BadgeRow),
            "room": array(RoomRow),
            "routine": array(RoutineRow),
            "other": array(OtherRow),
            "button": array(ButtonRow, types={"key": int}),
        },
        variables=os.environ,
    )

    badges = {row.action: Icon.parse(row.icon) for row in objects["badge"]}
    rooms = {row.slug: row for row in objects["room"]}
    routines = {row.slug: row for row in objects["routine"]}
    others = {row.slug: row for row in objects["other"]}

    keys = _keys(objects["button"], rooms, routines, others)
    return Parsed(
        settings=objects["setting"],
        badges=badges,
        buttons=keys.buttons,
        routines=keys.routines,
        others=keys.others,
        art=_art(rooms, routines, others, badges),
    )


def read(path: str | Path | None = None) -> Parsed:
    source = Path(path or os.getenv("ARROW_CONFIG") or CONFIG_PATH)
    return parse(source.read_text())


def _as_int(value: str, _objects: object = None) -> int:
    # scalar() calls a type with (value, objects); builtins.int reads the second as a base
    return int(value)


def _art(
    rooms: dict[str, RoomRow],
    routines: dict[str, RoutineRow],
    others: dict[str, OtherRow],
    badges: dict[str, Icon],
) -> dict[str, Art]:
    art: dict[str, Art] = {}
    for slug, room in rooms.items():
        for state in ACTIONS:
            art[f"{slug}/{state}"] = Art((Icon.parse(room.icon),), badge=badges.get(state))
    for slug, routine in routines.items():
        icons = (Icon.parse(routine.icon),) + ((Icon.parse(routine.icon2 or ""),) if routine.layout == "pair" else ())
        text = routine.text if routine.layout == "caption" else None
        badge = Icon.parse(routine.badge or "") if routine.layout == "marked" else None
        art[slug] = Art(icons, text=text, badge=badge)
    for slug, other in others.items():
        art[slug] = Art((Icon.parse(other.icon),))
    return art


def _keys(
    rows: list[ButtonRow],
    rooms: dict[str, RoomRow],
    routines: dict[str, RoutineRow],
    others: dict[str, OtherRow],
) -> Keys:
    buttons: dict[int, Button] = {}
    routine_keys: dict[int, Routine] = {}
    other_keys: dict[int, Other] = {}
    for row in rows:
        if row.key in buttons or row.key in routine_keys or row.key in other_keys:
            raise ConfigError(f"key {row.key} is claimed twice")
        if row.slug in rooms:
            if row.action not in ACTIONS:
                raise ConfigError(f"room button {row.slug!r} needs one of {ACTIONS}, got {row.action!r}")
            buttons[row.key] = Button(row.slug, rooms[row.slug].name, row.action)
        elif row.action:
            raise ConfigError(f"{row.slug!r} is not a room, so it takes no action (got {row.action!r})")
        elif row.slug in routines:
            routine = routines[row.slug]
            routine_keys[row.key] = Routine(row.slug, routine.name, routine.orc_id or f"AD_HOC_{row.slug.upper()}")
        elif row.slug in others:
            other_keys[row.key] = Other(row.slug, others[row.slug].name)
        else:
            raise ConfigError(f"button {row.slug!r} matches no room, routine or other")
    return Keys(buttons, routine_keys, other_keys)
