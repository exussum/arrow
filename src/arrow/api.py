import sys
import threading
from functools import partial
from itertools import chain
from pathlib import Path

from PIL import Image
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper

from arrow import (
    ACTIVE_BRIGHTNESS,
    BUTTONS,
    BUTTONS_BY_POSITION,
    DIM_BRIGHTNESS,
    DIM_DELAY_SECONDS,
    ICONS_DIR,
    OTHERS,
    PRESENCE_NAME,
    OtherId,
    ROUTINES,
    ROUTINES_BY_POSITION,
)
from arrow import dal
from arrow.models import Dispatch, NativeCache, State


_DISPATCH = {
    OtherId.presence.value: Dispatch(
        ICONS_DIR / "countdowns" / "presence.gif",
        partial(dal.call_presence, PRESENCE_NAME),
    ),
    **{pos: Dispatch(ICONS_DIR / "countdowns" / b.action / f"{b.slug}.gif",
                     partial(dal.call_room, b.display_name, b.action))
       for pos, b in BUTTONS_BY_POSITION.items()},
    **{pos: Dispatch(ICONS_DIR / "countdowns" / "routines" / f"{r.slug}.gif",
                     partial(dal.call_routine, r.display_name))
       for pos, r in ROUTINES_BY_POSITION.items()},
}


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
    )
    _upload_icons(deck)
    deck.set_brightness(DIM_BRIGHTNESS)


def shutdown_deck(deck):
    deck.set_brightness(0)
    with deck:
        deck.close()


def on_key_change(deck, state, key, pressed):
    if not pressed:
        return

    with state.lock:
        if state.brightness == DIM_BRIGHTNESS:
            deck.set_brightness(ACTIVE_BRIGHTNESS)
            state.brightness = ACTIVE_BRIGHTNESS
            _schedule_dim(deck, state)
            return

    if key == OtherId.help.value:
        with state.lock:
            state.show_labels = not state.show_labels
        _upload_icons(deck, state.show_labels)
        _schedule_dim(deck, state)
    elif (entry := _DISPATCH.get(key)) is not None:
        _run(deck, state, key, entry.gif, entry.action)
    else:
        print(f"button {key} unmapped", file=sys.stderr)


def _run(deck, state, key, gif_path, action):
    with state.lock:
        state.show_labels = False
    _cancel_dim(state)
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
        _upload_icons(deck, state.show_labels)
        _schedule_dim(deck, state)


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


def _upload_icons(deck, show_labels=False):
    icons = _cache.labels if show_labels else _cache.icons
    with deck:
        for key, native in icons.items():
            deck.set_key_image(key, native)


def _apply_brightness(deck, state, level):
    with state.lock:
        deck.set_brightness(level)
        state.brightness = level
        revert_to_icons = level == DIM_BRIGHTNESS and state.show_labels
        if revert_to_icons:
            state.show_labels = False
    if revert_to_icons:
        _upload_icons(deck, show_labels=False)


def _schedule_dim(deck, state):
    _cancel_dim(state)
    t = threading.Timer(DIM_DELAY_SECONDS, _apply_brightness, args=[deck, state, DIM_BRIGHTNESS])
    t.daemon = True
    t.start()
    state.dim_timer = t


def _cancel_dim(state):
    if state.dim_timer is not None:
        state.dim_timer.cancel()


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
        (id_value, path)
        for id_value, path in chain(
            ((bid.value, base / button.action / f"{button.slug}.png") for bid, button in BUTTONS.items()),
            ((rid.value, base / "routines" / f"{routine.slug}.png") for rid, routine in ROUTINES.items()),
            ((oid.value, base / f"{other.slug}.png") for oid, other in OTHERS.items()),
        )
    ]


def _gif_targets():
    return [entry.gif for entry in _DISPATCH.values()]


def _build_icon_cache(deck, label: bool = False):
    return {key: _open_native(deck, path) for key, path in _icon_targets(label)}


def _build_gif_cache(deck):
    return {path: _gif_frames_native(deck, path) for path in _gif_targets()}
