import io
import random
import threading
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any

from PIL import Image
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

from arrow.config import config, countdown_targets, icon_targets
from arrow.models import IconMode


@dataclass
class ImageManager:
    icons: dict[int, Any]
    labels: dict[int, Any]
    frames: dict[str, list[Any]]
    blank: dict[int, Any]
    delayed: dict[int, Any]

    @classmethod
    def build(cls, deck: Any) -> "ImageManager":
        with zipfile.ZipFile(config.icons) as archive:
            return cls(
                icons=cls._build_icon_cache(deck, archive, label=False),
                labels=cls._build_icon_cache(deck, archive, label=True),
                frames={name: cls._gif_frames_native(deck, archive, name) for _, name in countdown_targets()},
                blank=cls._build_cache(deck, PILHelper.create_image(deck)),
                delayed=cls._build_cache(deck, cls._open(archive, "delayed.png")),
            )

    @classmethod
    def _build_icon_cache(cls, deck: Any, archive: zipfile.ZipFile, label: bool = False) -> dict[int, Any]:
        return {key: cls._to_native(deck, cls._open(archive, name)) for key, name in icon_targets(label)}

    @classmethod
    def _build_cache(cls, deck: Any, image: Image.Image) -> dict[int, Any]:
        native = cls._to_native(deck, image)
        return {k: native for k in range(deck.key_count())}

    @staticmethod
    def _to_native(deck: Any, pil_img: Image.Image) -> Any:
        scaled = PILHelper.create_scaled_image(deck, pil_img, margins=[0, 0, 0, 0])
        return PILHelper.to_native_format(deck, scaled)

    @staticmethod
    def _open(archive: zipfile.ZipFile, name: str) -> Image.Image:
        return Image.open(io.BytesIO(archive.read(name)))

    @classmethod
    def _gif_frames_native(cls, deck: Any, archive: zipfile.ZipFile, name: str) -> list[Any]:
        frames = []
        img = cls._open(archive, name)
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

    def play_countdown(self, key: int, gif: str, done: threading.Event) -> None:
        frames = self._cache.frames[gif]
        last = len(frames) - 1
        for i, native in enumerate(frames):
            self._set_key_image(key, native)
            if done.wait(timeout=None if i == last else 1.0):
                return


def open_deck() -> Any:
    decks = DeviceManager().enumerate()
    if not decks:
        raise RuntimeError("no StreamDeck found")
    deck = decks[0]
    deck.open()
    return deck
