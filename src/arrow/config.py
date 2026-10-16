from itertools import chain
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from command_cfg import ConfigError

from arrow import loader

ICONS_DIR = Path(__file__).resolve().parent / "icons"


class ConfigNotLoadedError(AttributeError):
    pass


class Config:
    def __getattr__(self, name: str) -> Any:
        raise ConfigNotLoadedError(f"arrow config not loaded (reading {name!r}): the entry point must call config.load() first")

    def load(self, path: str | Path | None = None) -> None:
        self._install(loader.read(path))

    def _install(self, parsed: SimpleNamespace) -> None:
        self.settings = parsed.settings
        self.badges = parsed.badges
        self.buttons = parsed.buttons
        self.routines = parsed.routines
        self.others = parsed.others
        self.art = parsed.art

    def key_of(self, slug: str) -> int:
        for key, other in self.others.items():
            if other.slug == slug:
                return key
        raise ConfigError(f"no button declared for {slug!r}")


config = Config()


def icon_targets(label: bool = False) -> list[tuple[int, Path]]:
    base = ICONS_DIR / "labels" if label else ICONS_DIR
    return list(
        chain(
            ((key, base / button.action / f"{button.slug}.png") for key, button in config.buttons.items()),
            ((key, base / "routines" / f"{routine.slug}.png") for key, routine in config.routines.items()),
            ((key, base / f"{other.slug}.png") for key, other in config.others.items()),
        )
    )


def countdown_targets() -> list[tuple[int, Path]]:
    base = ICONS_DIR / "countdowns"
    return list(
        chain(
            ((key, base / "presence.gif") for key, other in config.others.items() if other.slug == "presence"),
            ((key, base / button.action / f"{button.slug}.gif") for key, button in config.buttons.items()),
            ((key, base / "routines" / f"{routine.slug}.gif") for key, routine in config.routines.items()),
        )
    )
