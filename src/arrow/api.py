import random
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial, wraps
from itertools import chain
from pathlib import Path
from typing import Any

from PIL import Image
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

from arrow import (
    ACTIVE_BRIGHTNESS,
    BUTTONS,
    BUTTONS_BY_POSITION,
    DELAY_NOTICE_SECONDS,
    DIM_BRIGHTNESS,
    DIM_DELAY_SECONDS,
    ICONS_DIR,
    OTHERS,
    PRESENCE_NAME,
    ROUTINES,
    ROUTINES_BY_POSITION,
    OtherId,
    dal,
)
from arrow.img import SIZE, delayed_frame
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
            delayed=cls._build_cache(deck, delayed_frame()),
        )

    @classmethod
    def _build_icon_cache(cls, deck: Any, label: bool = False) -> dict[int, Any]:
        return {key: cls._open_native(deck, path) for key, path in cls._icon_targets(label)}

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

    @staticmethod
    def _icon_targets(label: bool = False) -> list[tuple[int, Path]]:
        base = ICONS_DIR / "labels" if label else ICONS_DIR
        return [
            (id_value, path)
            for id_value, path in chain(
                ((bid.value, base / button.action / f"{button.slug}.png") for bid, button in BUTTONS.items()),
                ((rid.value, base / "routines" / f"{routine.slug}.png") for rid, routine in ROUTINES.items()),
                ((oid.value, base / f"{other.slug}.png") for oid, other in OTHERS.items()),
            )
        ]


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


class DeckManager:
    _DISPATCH = {
        OtherId.presence.value: Dispatch(
            ICONS_DIR / "countdowns" / "presence.gif",
            partial(dal.call_presence, PRESENCE_NAME),
        ),
        **{
            pos: Dispatch(
                ICONS_DIR / "countdowns" / b.action / f"{b.slug}.gif",
                partial(dal.call_room, b.display_name, b.action),
                b.display_name,
            )
            for pos, b in BUTTONS_BY_POSITION.items()
        },
        **{
            pos: Dispatch(
                ICONS_DIR / "countdowns" / "routines" / f"{r.slug}.gif",
                partial(dal.call_routine, r.display_name),
                r.display_name,
            )
            for pos, r in ROUTINES_BY_POSITION.items()
        },
    }

    def __init__(self, brightness: int, display: DisplayManager) -> None:
        self._brightness = brightness
        self._display = display
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
            gif_paths = [entry.gif for entry in cls._DISPATCH.values()]
            cache = ImageManager.build(deck, gif_paths)
        except Exception:
            deck.close()
            raise
        return cls(brightness=brightness, display=DisplayManager(deck=deck, cache=cache))

    def initialize(self) -> None:
        self._display.deck.reset()
        self._display.upload_icons(IconMode.ICONS)
        self.set_brightness(DIM_BRIGHTNESS)
        self._display.deck.set_key_callback(lambda d, k, p: self.on_key_change(k, p))

    def shutdown(self) -> None:
        self._cancel_dim()
        self._display.close()

    def set_brightness(self, level: int) -> None:
        self._display.set_brightness(level)
        self._brightness = level
        if level == DIM_BRIGHTNESS:
            self._display.on_dim()

    def on_key_change(self, key: int, pressed: bool) -> None:
        if not pressed:
            return
        elif self._brightness == DIM_BRIGHTNESS:
            self.set_brightness(ACTIVE_BRIGHTNESS)
            self._schedule_dim()
        elif key == OtherId.help.value:
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
        if name is not None and dal.get_delay(name) is not None:
            self._display.show_delayed_notice(key)
            time.sleep(DELAY_NOTICE_SECONDS)

    def _schedule_dim(self) -> None:
        self._cancel_dim()
        with self._dim_lock:
            self._dim_active = True
        t = threading.Timer(DIM_DELAY_SECONDS, self._apply_dim)
        t.daemon = True
        t.start()
        self._dim_timer = t

    def _apply_dim(self) -> None:
        with self._dim_lock:
            if self._dim_active:
                self._dim_active = False
                self.set_brightness(DIM_BRIGHTNESS)

    def _cancel_dim(self) -> None:
        with self._dim_lock:
            self._dim_active = False
        if self._dim_timer is not None:
            self._dim_timer.cancel()
            self._dim_timer = None
