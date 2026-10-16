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
