import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import command_cfg
from command_cfg import ConfigError, array, scalar

from arrow.models import Button, Other, Routine

CONFIG_PATH = Path(__file__).resolve().parent / "config.arrow"

ACTIONS = ("on", "off", "follow")
FILTERS = ("dim", "invert")

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


def _as_int(value: str, _objects: object = None) -> int:
    # scalar() calls a type with (value, objects); builtins.int reads the second as a base
    return int(value)


def _layout(row: SimpleNamespace) -> str:
    return next(name for name in ("single", "pair", "caption", "marked") if getattr(row, name, False))


def _opt(row: SimpleNamespace, name: str) -> str | None:
    # command-cfg omits absent optional fields rather than passing None
    return getattr(row, name, None)


def parse(text: str) -> SimpleNamespace:
    row = lambda **kw: SimpleNamespace(**kw)  # noqa: E731
    objects = command_cfg.load(
        text,
        GRAMMAR,
        {
            "setting": scalar(Settings, types=dict.fromkeys(Settings.INTS, _as_int)),
            "badge": array(row),
            "room": array(row),
            "routine": array(row),
            "other": array(row),
            "button": array(row, types={"key": int}),
        },
        variables=os.environ,
    )

    badges = {b.action: Icon.parse(b.icon) for b in objects["badge"]}
    rooms = {r.slug: r for r in objects["room"]}
    routines = {r.slug: r for r in objects["routine"]}
    others = {o.slug: o for o in objects["other"]}

    art: dict[str, Art] = {}
    for slug, r in rooms.items():
        for state in ACTIONS:
            art[f"{slug}/{state}"] = Art((Icon.parse(r.icon),), badge=badges.get(state))
    for slug, r in routines.items():
        kind = _layout(r)
        icons = (Icon.parse(r.icon),) + ((Icon.parse(_opt(r, "icon2") or ""),) if kind == "pair" else ())
        art[slug] = Art(
            icons,
            text=_opt(r, "text") if kind == "caption" else None,
            badge=Icon.parse(_opt(r, "badge") or "") if kind == "marked" else None,
        )
    for slug, o in others.items():
        art[slug] = Art((Icon.parse(o.icon),))

    buttons: dict[int, Button] = {}
    routine_keys: dict[int, Routine] = {}
    other_keys: dict[int, Other] = {}
    for b in objects["button"]:
        action = _opt(b, "action")
        if b.key in buttons or b.key in routine_keys or b.key in other_keys:
            raise ConfigError(f"key {b.key} is claimed twice")
        if b.slug in rooms:
            if action not in ACTIONS:
                raise ConfigError(f"room button {b.slug!r} needs one of {ACTIONS}, got {action!r}")
            buttons[b.key] = Button(b.slug, rooms[b.slug].name, action)
        elif action is not None:
            raise ConfigError(f"{b.slug!r} is not a room, so it takes no action (got {action!r})")
        elif b.slug in routines:
            r = routines[b.slug]
            buttons_id = _opt(r, "orc_id") or f"AD_HOC_{b.slug.upper()}"
            routine_keys[b.key] = Routine(b.slug, r.name, buttons_id)
        elif b.slug in others:
            other_keys[b.key] = Other(b.slug, others[b.slug].name)
        else:
            raise ConfigError(f"button {b.slug!r} matches no room, routine or other")

    return SimpleNamespace(
        settings=objects["setting"],
        badges=badges,
        buttons=buttons,
        routines=routine_keys,
        others=other_keys,
        art=art,
    )


def read(path: str | Path | None = None) -> SimpleNamespace:
    source = Path(path or os.getenv("ARROW_CONFIG") or CONFIG_PATH)
    return parse(source.read_text())
