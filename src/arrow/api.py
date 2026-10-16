import random
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial, wraps
from pathlib import Path
from typing import Any

from PIL import Image
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

from arrow import dal
from arrow.config import ICONS_DIR, config, icon_targets
from arrow.img import SIZE
from arrow.models import Dispatch, IconMode


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
            blank=cls._build_cache(deck, Image.new("RGB", (SIZE, SIZE), "black")),
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


def build_dispatch() -> dict[int, Dispatch]:
    presence = {
        key: Dispatch(ICONS_DIR / "countdowns" / "presence.gif", partial(dal.call_presence, config.settings.presence_name))
        for key, other in config.others.items()
        if other.slug == "presence"
    }
    rooms = {
        key: Dispatch(
            ICONS_DIR / "countdowns" / b.action / f"{b.slug}.gif",
            partial(dal.call_room, b.display_name, b.action),
            b.display_name,
        )
        for key, b in config.buttons.items()
    }
    routines = {
        key: Dispatch(
            ICONS_DIR / "countdowns" / "routines" / f"{r.slug}.gif",
            partial(dal.call_routine, r.orc_id or r.display_name, r.display_name),
            r.orc_id or r.display_name,
        )
        for key, r in config.routines.items()
    }
    return presence | rooms | routines


class DeckManager:
    def __init__(self, brightness: int, display: DisplayManager) -> None:
        self._brightness = brightness
        self._display = display
        self._DISPATCH = build_dispatch()
        self._dim_timer: threading.Timer | None = None
        self._dim_lock = threading.Lock()
        self._dim_active = False

    @classmethod
    def build_manager(cls, brightness: int) -> "DeckManager":
        decks = DeviceManager().enumerate()
        if not decks:
            raise RuntimeError("no StreamDeck found")
        deck = decks[0]
        deck.open()
        try:
            gif_paths = [entry.gif for entry in build_dispatch().values()]
            cache = ImageManager.build(deck, gif_paths)
        except Exception:
            deck.close()
            raise
        return cls(brightness=brightness, display=DisplayManager(deck=deck, cache=cache))

    def initialize(self) -> None:
        self._display.deck.reset()
        self._display.upload_icons(IconMode.ICONS)
        self.set_brightness(config.settings.dim_brightness)
        self._display.deck.set_key_callback(lambda d, k, p: self.on_key_change(k, p))

    def shutdown(self) -> None:
        self._cancel_dim()
        self._display.close()

    def set_brightness(self, level: int) -> None:
        self._display.set_brightness(level)
        self._brightness = level
        if level == config.settings.dim_brightness:
            self._display.on_dim()

    def on_key_change(self, key: int, pressed: bool) -> None:
        if not pressed:
            return
        elif self._brightness == config.settings.dim_brightness:
            self.set_brightness(config.settings.active_brightness)
            self._schedule_dim()
        elif key == config.key_of("help"):
            self._display.toggle_labels()
            self._schedule_dim()
        elif (entry := self._DISPATCH.get(key)) is not None:
            self._display.upload_icons(IconMode.BLANK)
            self._cancel_dim()
            self._run(key, entry.gif, entry.action, entry.name)
        else:
            print(f"button {key} unmapped", file=sys.stderr)

    def _run(self, key: int, gif_path: Path, action: Callable[[], object], name: str | None = None) -> None:
        self._notify_delay(key, name)
        done = threading.Event()
        animator = threading.Thread(
            target=self._display.play_countdown,
            args=(key, gif_path, done),
            daemon=True,
        )
        animator.start()
        try:
            action()
        finally:
            done.set()
            animator.join(timeout=5)
            self._display.upload_icons(IconMode.ICONS)
            self._schedule_dim()

    def _notify_delay(self, key: int, name: str | None) -> None:
        if name is not None and dal.get_delay(name):
            self._display.show_delayed_notice(key)
            time.sleep(config.settings.delay_notice_seconds)

    def _schedule_dim(self) -> None:
        self._cancel_dim()
        with self._dim_lock:
            self._dim_active = True
        t = threading.Timer(config.settings.dim_delay_seconds, self._apply_dim)
        t.daemon = True
        t.start()
        self._dim_timer = t

    def _apply_dim(self) -> None:
        with self._dim_lock:
            if self._dim_active:
                self._dim_active = False
                self.set_brightness(config.settings.dim_brightness)

    def _cancel_dim(self) -> None:
        with self._dim_lock:
            self._dim_active = False
        if self._dim_timer is not None:
            self._dim_timer.cancel()
            self._dim_timer = None
