import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import command_cfg
from command_cfg import ConfigError, array, scalar

from arrow.models import Button, Other, Routine

ACTIONS = ("on", "off", "follow")
FILTERS = ("dim", "invert")
LAYOUTS = ("single", "pair", "caption", "marked")

AD_HOC_PREFIX = "AD_HOC_"
RESERVED = ("help", "presence")

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


class Icon(NamedTuple):
    char: str
    filter: str | None = None


class Single(NamedTuple):
    icon: Icon


class Pair(NamedTuple):
    first: Icon
    second: Icon


class Caption(NamedTuple):
    icon: Icon
    text: str


class Marked(NamedTuple):
    icon: Icon
    badge: Icon


Art = Single | Pair | Caption | Marked


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
    reserved: dict[str, int]


class Parsed(NamedTuple):
    settings: Settings
    reserved: dict[str, int]
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

    badges = {row.action: _icon(row.icon) for row in objects["badge"]}
    rooms = {row.slug: row for row in objects["room"]}
    if rooms and (undeclared := [state for state in ACTIONS if state not in badges]):
        raise ConfigError(f"rooms need a badge line for each state; missing {', '.join(undeclared)}")
    routines = {row.slug: row for row in objects["routine"]}
    others = {row.slug: row for row in objects["other"]}

    keys = _keys(objects["button"], rooms, routines, others)
    return Parsed(
        settings=objects["setting"],
        reserved=keys.reserved,
        badges=badges,
        buttons=keys.buttons,
        routines=keys.routines,
        others=keys.others,
        art=_art(rooms, routines, others, badges),
    )


def source(path: str | Path | None = None) -> Path:
    if found := path or os.getenv("ARROW_CONFIG"):
        return Path(found)
    raise ConfigError("no config: pass --config or set ARROW_CONFIG")


def _icon(spec: str) -> Icon:
    name, _, flt = spec.partition(":")
    if flt and flt not in FILTERS:
        raise ConfigError(f"unknown icon filter {flt!r}: expected one of {FILTERS}")
    try:
        return Icon(unicodedata.lookup(name.replace("-", " ").upper()), flt or None)
    except KeyError:
        raise ConfigError(f"unknown icon name {name!r}") from None


def _as_int(value: str, _objects: object = None) -> int:
    return int(value)


def _art(
    rooms: dict[str, RoomRow],
    routines: dict[str, RoutineRow],
    others: dict[str, OtherRow],
    badges: dict[str, Icon],
) -> dict[str, Art]:
    art: dict[str, Art] = {}
    for slug, room in rooms.items():
        icon = _icon(room.icon)
        for state in ACTIONS:
            art[f"{slug}/{state}"] = Marked(icon, badges[state])
    for slug, routine in routines.items():
        icon = _icon(routine.icon)
        match routine.layout:
            case "pair":
                art[slug] = Pair(icon, _icon(routine.icon2 or ""))
            case "caption":
                art[slug] = Caption(icon, routine.text or "")
            case "marked":
                art[slug] = Marked(icon, _icon(routine.badge or ""))
            case _:
                art[slug] = Single(icon)
    for slug, other in others.items():
        art[slug] = Single(_icon(other.icon))
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
    claimed: set[int] = set()
    for row in rows:
        if row.key in claimed:
            raise ConfigError(f"key {row.key} is claimed twice")
        claimed.add(row.key)

        room = rooms.get(row.slug)
        if not room and row.action:
            raise ConfigError(f"{row.slug!r} is not a room, so it takes no action (got {row.action!r})")
        elif room:
            if row.action is None or row.action not in ACTIONS:
                raise ConfigError(f"room button {row.slug!r} needs one of {ACTIONS}, got {row.action!r}")
            buttons[row.key] = Button(row.slug, room.name, row.action)
        elif routine := routines.get(row.slug):
            routine_keys[row.key] = Routine(row.slug, routine.name, routine.orc_id or f"{AD_HOC_PREFIX}{row.slug.upper()}")
        elif other := others.get(row.slug):
            other_keys[row.key] = Other(row.slug, other.name)
        else:
            raise ConfigError(f"button {row.slug!r} matches no room, routine or other")

    reserved = {slug: key for key, other in other_keys.items() for slug in RESERVED if other.slug == slug}
    if undeclared := [slug for slug in RESERVED if slug not in reserved]:
        raise ConfigError(f"no button line for reserved slug(s): {', '.join(undeclared)}")
    return Keys(buttons, routine_keys, other_keys, reserved)
