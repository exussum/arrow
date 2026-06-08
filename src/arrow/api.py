import sys
import threading
from datetime import datetime, timedelta
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
    ICONS_DIR,
    ROUTINES,
    ROUTINES_BY_POSITION,
)
from arrow import dal


def get_deck():
    decks = DeviceManager().enumerate()
    deck = decks[0]
    deck.open()
    return deck


_NATIVE_ICONS: dict[int, bytes] = {}
_NATIVE_FRAMES: dict[Path, list[tuple[bytes, float]]] = {}
_NATIVE_BLANK: bytes | None = None


def initialize_deck(deck):
    global _NATIVE_BLANK
    deck.reset()
    _build_icon_cache(deck)
    _build_gif_cache(deck)
    _NATIVE_BLANK = _to_native(deck, Image.new("RGB", (144, 144), "black"))
    _upload_icons(deck)
    deck.set_brightness(DIM_BRIGHTNESS)


def shutdown_deck(deck):
    deck.set_brightness(0)
    with deck:
        deck.close()


class State:
    def __init__(self, brightness):
        self.brightness = brightness
        self.lock = threading.Lock()


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


def on_key_change(deck, state, scheduler, key, pressed):
    if not pressed:
        return

    with state.lock:
        if state.brightness == DIM_BRIGHTNESS:
            deck.set_brightness(ACTIVE_BRIGHTNESS)
            state.brightness = ACTIVE_BRIGHTNESS
            _schedule_dim(scheduler, deck, state)
            return

    button = BUTTONS_BY_POSITION.get(key)
    if button is not None:
        gif = ICONS_DIR / "countdowns" / button.action / f"{button.slug}.gif"
        _run(deck, state, scheduler, key, gif, lambda: dal.call_room(button.display_name, button.action))
        return

    routine = ROUTINES_BY_POSITION.get(key)
    if routine is not None:
        gif = ICONS_DIR / "countdowns" / "routines" / f"{routine.slug}.gif"
        _run(deck, state, scheduler, key, gif, lambda: dal.call_routine(routine.display_name))
        return

    print(f"button {key} unmapped", file=sys.stderr)


def _to_native(deck, pil_img):
    scaled = PILHelper.create_scaled_image(deck, pil_img, margins=[0, 0, 0, 0])
    return PILHelper.to_native_format(deck, scaled)


def _gif_frames_native(deck, path: Path):
    frames = []
    with Image.open(path) as img:
        for i in range(img.n_frames):
            img.seek(i)
            duration_ms = img.info.get("duration", 1000)
            frames.append((_to_native(deck, img.convert("RGB")), duration_ms / 1000.0))
    return frames


def _play_countdown(deck, key, gif_path, done):
    frames = _NATIVE_FRAMES[gif_path]
    with deck:
        for k in range(deck.key_count()):
            if k != key:
                deck.set_key_image(k, _NATIVE_BLANK)

    for i, (native, duration) in enumerate(frames):
        with deck:
            deck.set_key_image(key, native)
        timeout = None if i == len(frames) - 1 else duration
        if done.wait(timeout=timeout):
            return


def _run(deck, state, scheduler, key, gif_path, action):
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
        _upload_icons(deck)
        _schedule_dim(scheduler, deck, state)


def _icon_targets():
    targets = [
        (bid.value, ICONS_DIR / button.action / f"{button.slug}.png")
        for bid, button in BUTTONS.items()
    ]
    targets += [
        (rid.value, ICONS_DIR / "routines" / f"{routine.slug}.png")
        for rid, routine in ROUTINES.items()
    ]
    return targets


def _build_icon_cache(deck):
    _NATIVE_ICONS.clear()
    for key, path in _icon_targets():
        with Image.open(path) as img:
            _NATIVE_ICONS[key] = _to_native(deck, img)
    print(f"cached {len(_NATIVE_ICONS)} icons", file=sys.stderr)


def _gif_targets():
    targets = [
        ICONS_DIR / "countdowns" / b.action / f"{b.slug}.gif"
        for b in BUTTONS.values()
    ]
    targets += [
        ICONS_DIR / "countdowns" / "routines" / f"{r.slug}.gif"
        for r in ROUTINES.values()
    ]
    return targets


def _build_gif_cache(deck):
    _NATIVE_FRAMES.clear()
    total = 0
    for path in _gif_targets():
        frames = _gif_frames_native(deck, path)
        _NATIVE_FRAMES[path] = frames
        total += len(frames)
    print(f"cached {len(_NATIVE_FRAMES)} countdowns ({total} frames)", file=sys.stderr)


def _upload_icons(deck):
    with deck:
        for key, native in _NATIVE_ICONS.items():
            deck.set_key_image(key, native)
