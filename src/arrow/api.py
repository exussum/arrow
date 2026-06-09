import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import chain
from pathlib import Path

from apscheduler.jobstores.base import JobLookupError
from PIL import Image
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

from arrow import (
    ACTIVE_BRIGHTNESS,
    BUTTONS,
    BUTTONS_BY_POSITION,
    DIM_BRIGHTNESS,
    DIM_DELAY_SECONDS,
    HELP_POSITION,
    ICONS_DIR,
    ROUTINES,
    ROUTINES_BY_POSITION,
)
from arrow import dal


@dataclass
class NativeCache:
    icons: dict[int, bytes]
    labels: dict[int, bytes]
    frames: dict[Path, list[bytes]]
    blank: bytes
    help: bytes


class State:
    def __init__(self, brightness):
        self.brightness = brightness
        self.show_labels = False
        self.lock = threading.Lock()


def get_deck():
    decks = DeviceManager().enumerate()
    deck = decks[0]
    deck.open()
    return deck


def initialize_deck(deck):
    global _cache
    deck.reset()
    _cache = NativeCache(
        icons=_build_icon_cache(deck, label=False),
        labels=_build_icon_cache(deck, label=True),
        frames=_build_gif_cache(deck),
        blank=_to_native(deck, Image.new("RGB", (144, 144), "black")),
        help=_open_native(deck, ICONS_DIR / "help.png"),
    )
    _upload_icons(deck)
    deck.set_brightness(DIM_BRIGHTNESS)


def shutdown_deck(deck):
    deck.set_brightness(0)
    with deck:
        deck.close()


def on_key_change(deck, state, scheduler, key, pressed):
    if not pressed:
        return

    with state.lock:
        if state.brightness == DIM_BRIGHTNESS:
            deck.set_brightness(ACTIVE_BRIGHTNESS)
            state.brightness = ACTIVE_BRIGHTNESS
            _schedule_dim(scheduler, deck, state)
            return

    if key == HELP_POSITION:
        with state.lock:
            state.show_labels = not state.show_labels
        _upload_icons(deck, state)
        _schedule_dim(scheduler, deck, state)
    elif (button := BUTTONS_BY_POSITION.get(key)) is not None:
        gif = ICONS_DIR / "countdowns" / button.action / f"{button.slug}.gif"
        _run(deck, state, scheduler, key, gif, lambda: dal.call_room(button.display_name, button.action))
    elif (routine := ROUTINES_BY_POSITION.get(key)) is not None:
        gif = ICONS_DIR / "countdowns" / "routines" / f"{routine.slug}.gif"
        _run(deck, state, scheduler, key, gif, lambda: dal.call_routine(routine.display_name))
    else:
        print(f"button {key} unmapped", file=sys.stderr)


def _run(deck, state, scheduler, key, gif_path, action):
    with state.lock:
        state.show_labels = False
    _cancel_dim(scheduler)
    done = threading.Event()
    animator = threading.Thread(
        target=_play_countdown,
        args=(deck, key, gif_path, done),
        daemon=True,
    )
    animator.start()
    try:
        action()
    finally:
        done.set()
        animator.join(timeout=5)
        _upload_icons(deck, state)
        _schedule_dim(scheduler, deck, state)


def _play_countdown(deck, key, gif_path, done):
    frames = _cache.frames[gif_path]
    with deck:
        for k in range(deck.key_count()):
            if k != key:
                deck.set_key_image(k, _cache.blank)

    last = len(frames) - 1
    for i, native in enumerate(frames):
        with deck:
            deck.set_key_image(key, native)
        if done.wait(timeout=None if i == last else 1.0):
            return


def _upload_icons(deck, state=None):
    show_labels = state.show_labels if state is not None else False
    icons = _cache.labels if show_labels else _cache.icons
    with deck:
        for key, native in icons.items():
            deck.set_key_image(key, native)
        deck.set_key_image(HELP_POSITION, _cache.help)


def _apply_brightness(deck, state, level):
    with state.lock:
        deck.set_brightness(level)
        state.brightness = level


def _schedule_dim(scheduler, deck, state):
    scheduler.add_job(
        _apply_brightness,
        "date",
        run_date=datetime.now() + timedelta(seconds=DIM_DELAY_SECONDS),
        args=[deck, state, DIM_BRIGHTNESS],
        id="dim",
        replace_existing=True,
    )


def _cancel_dim(scheduler):
    try:
        scheduler.remove_job("dim")
    except JobLookupError:
        pass


def _to_native(deck, pil_img):
    scaled = PILHelper.create_scaled_image(deck, pil_img, margins=[0, 0, 0, 0])
    return PILHelper.to_native_format(deck, scaled)


def _open_native(deck, path: Path):
    with Image.open(path) as img:
        return _to_native(deck, img)


def _gif_frames_native(deck, path: Path):
    frames = []
    with Image.open(path) as img:
        for i in range(img.n_frames):
            img.seek(i)
            frames.append(_to_native(deck, img.convert("RGB")))
    return frames


def _icon_targets(label: bool = False):
    base = ICONS_DIR / "labels" if label else ICONS_DIR
    return [
        (id_value, base / action / f"{slug}.png")
        for id_value, action, slug in chain(
            ((bid.value, button.action, button.slug) for bid, button in BUTTONS.items()),
            ((rid.value, "routines", routine.slug) for rid, routine in ROUTINES.items()),
        )
    ]


def _gif_targets():
    return [
        ICONS_DIR / "countdowns" / action / f"{slug}.gif"
        for action, slug in chain(
            ((b.action, b.slug) for b in BUTTONS.values()),
            (("routines", r.slug) for r in ROUTINES.values()),
        )
    ]


def _build_icon_cache(deck, label: bool = False):
    cache = {key: _open_native(deck, path) for key, path in _icon_targets(label)}
    kind = "labels" if label else "icons"
    print(f"cached {len(cache)} {kind}", file=sys.stderr)
    return cache


def _build_gif_cache(deck):
    cache = {path: _gif_frames_native(deck, path) for path in _gif_targets()}
    total = sum(len(frames) for frames in cache.values())
    print(f"cached {len(cache)} countdowns ({total} frames)", file=sys.stderr)
    return cache
