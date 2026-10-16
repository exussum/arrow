from itertools import chain
from pathlib import Path
from typing import Any

from command_cfg import ConfigError

from arrow import loader
from arrow.loader import Parsed

ICONS_ZIP = "icons.zip"


class ConfigNotLoadedError(AttributeError):
    pass


class Config:
    def __getattr__(self, name: str) -> Any:
        raise ConfigNotLoadedError(f"arrow config not loaded (reading {name!r}): the entry point must call config.load() first")

    def load(self, path: str | Path | None = None, icons: str | Path | None = None) -> None:
        self.source = loader.source(path)
        self.icons = Path(icons) if icons else self.source.parent / ICONS_ZIP
        self._install(loader.parse(self.source.read_text()))

    def _install(self, parsed: Parsed) -> None:
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


def icon_targets(label: bool = False) -> list[tuple[int, str]]:
    base = "labels/" if label else ""
    return list(
        chain(
            ((key, f"{base}{button.action}/{button.slug}.png") for key, button in config.buttons.items()),
            ((key, f"{base}routines/{routine.slug}.png") for key, routine in config.routines.items()),
            ((key, f"{base}{other.slug}.png") for key, other in config.others.items()),
        )
    )


def countdown_targets() -> list[tuple[int, str]]:
    return list(
        chain(
            ((key, "countdowns/presence.gif") for key, other in config.others.items() if other.slug == "presence"),
            ((key, f"countdowns/{button.action}/{button.slug}.gif") for key, button in config.buttons.items()),
            ((key, f"countdowns/routines/{routine.slug}.gif") for key, routine in config.routines.items()),
        )
    )
