import random
import threading
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any

from PIL import Image
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

from arrow.config import ICONS_DIR, icon_targets
from arrow.models import IconMode


def open_deck() -> Any:
    decks = DeviceManager().enumerate()
    if not decks:
        raise RuntimeError("no StreamDeck found")
    deck = decks[0]
    deck.open()
    return deck


@dataclass
class ImageManager:
    icons: dict[int, Any]
    labels: dict[int, Any]
    frames: dict[Path, list[Any]]
    blank: dict[int, Any]
    delayed: dict[int, Any]

    @classmethod
    def build(cls, deck: Any, gif_paths: list[Path]) -> "ImageManager":
        return cls(
            icons=cls._build_icon_cache(deck, label=False),
            labels=cls._build_icon_cache(deck, label=True),
            frames=cls._build_gif_cache(deck, gif_paths),
            blank=cls._build_cache(deck, PILHelper.create_image(deck)),
            delayed=cls._build_cache(deck, Image.open(ICONS_DIR / "delayed.png")),
        )

    @classmethod
    def _build_icon_cache(cls, deck: Any, label: bool = False) -> dict[int, Any]:
        return {key: cls._open_native(deck, path) for key, path in icon_targets(label)}

    @classmethod
    def _build_cache(cls, deck: Any, image: Image.Image) -> dict[int, Any]:
        native = cls._to_native(deck, image)
        return {k: native for k in range(deck.key_count())}

    @classmethod
    def _build_gif_cache(cls, deck: Any, gif_paths: list[Path]) -> dict[Path, list[Any]]:
        return {path: cls._gif_frames_native(deck, path) for path in gif_paths}

    @staticmethod
    def _to_native(deck: Any, pil_img: Image.Image) -> Any:
        scaled = PILHelper.create_scaled_image(deck, pil_img, margins=[0, 0, 0, 0])
        return PILHelper.to_native_format(deck, scaled)

    @classmethod
    def _open_native(cls, deck: Any, path: Path) -> Any:
        with Image.open(path) as img:
            return cls._to_native(deck, img)

    @classmethod
    def _gif_frames_native(cls, deck: Any, path: Path) -> list[Any]:
        frames = []
        with Image.open(path) as img:
            for i in range(getattr(img, "n_frames")):
                img.seek(i)
                frames.append(cls._to_native(deck, img.convert("RGB")))
        return frames


def with_deck(method: Callable) -> Callable:
    @wraps(method)
    def wrapper(self: "DisplayManager", *args: Any, **kwargs: Any) -> Any:
        with self.deck:
            return method(self, *args, **kwargs)

    return wrapper


class DisplayManager:
    def __init__(self, deck: Any, cache: ImageManager) -> None:
        self.deck = deck
        self._cache = cache
        self._show_labels = False

    @with_deck
    def upload_icons(self, mode: IconMode) -> None:
        self._show_labels = mode == IconMode.LABELS
        match mode:
            case IconMode.BLANK:
                icons = self._cache.blank
            case IconMode.LABELS:
                icons = self._cache.labels
            case IconMode.ICONS:
                icons = self._cache.icons
            case _:
                raise ValueError(f"unhandled IconMode: {mode}")
        items = list(icons.items())
        random.shuffle(items)
        for key, native in items:
            self.deck.set_key_image(key, native)

    @with_deck
    def set_brightness(self, level: int) -> None:
        self.deck.set_brightness(level)

    @with_deck
    def close(self) -> None:
        self.deck.set_brightness(0)
        self.deck.close()

    def toggle_labels(self) -> None:
        self.upload_icons(IconMode.ICONS if self._show_labels else IconMode.LABELS)

    def on_dim(self) -> None:
        if self._show_labels:
            self.upload_icons(IconMode.ICONS)

    @with_deck
    def _set_key_image(self, key: int, native: Any) -> None:
        self.deck.set_key_image(key, native)

    def show_delayed_notice(self, key: int) -> None:
        self._set_key_image(key, self._cache.delayed[key])

    def play_countdown(self, key: int, gif_path: Path, done: threading.Event) -> None:
        frames = self._cache.frames[gif_path]
        last = len(frames) - 1
        for i, native in enumerate(frames):
            self._set_key_image(key, native)
            if done.wait(timeout=None if i == last else 1.0):
                return
