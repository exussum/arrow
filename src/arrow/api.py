import sys
import threading
from datetime import datetime, timedelta

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


def initialize_deck(deck):
    deck.reset()
    upload_icons(deck)
    deck.set_brightness(DIM_BRIGHTNESS)


def shutdown_deck(deck):
    deck.set_brightness(0)
    with deck:
        deck.close()


class State:
    def __init__(self, brightness):
        self.brightness = brightness
        self.lock = threading.Lock()


def apply_brightness(deck, state, level):
    with state.lock:
        deck.set_brightness(level)
        state.brightness = level


def on_key_change(deck, state, scheduler, key, pressed):
    if not pressed:
        return

    with state.lock:
        if state.brightness == DIM_BRIGHTNESS:
            deck.set_brightness(ACTIVE_BRIGHTNESS)
            state.brightness = ACTIVE_BRIGHTNESS
            scheduler.add_job(
                apply_brightness,
                "date",
                run_date=datetime.now() + timedelta(seconds=DIM_DELAY_SECONDS),
                args=[deck, state, DIM_BRIGHTNESS],
                id="dim",
                replace_existing=True,
            )
            return

    button = BUTTONS_BY_POSITION.get(key)
    if button is not None:
        dal.call_room(button.display_name, button.action)
        return

    routine = ROUTINES_BY_POSITION.get(key)
    if routine is not None:
        dal.call_routine(routine.display_name)
        return

    print(f"button {key} unmapped", file=sys.stderr)


def upload_icons(deck):
    targets = []
    for bid, button in BUTTONS.items():
        targets.append((
            bid.value,
            ICONS_DIR / button.action / f"{button.slug}.png",
            f"{button.display_name} {button.action}",
        ))
    for rid, routine in ROUTINES.items():
        targets.append((
            rid.value,
            ICONS_DIR / "routines" / f"{routine.slug}.png",
            routine.display_name,
        ))

    total = len(targets)
    for i, (key, path, label) in enumerate(targets, 1):
        with Image.open(path) as img:
            scaled = PILHelper.create_scaled_image(deck, img, margins=[0, 0, 0, 0])
        native = PILHelper.to_native_format(deck, scaled)
        with deck:
            deck.set_key_image(key, native)
    print(f"uploaded {total} icons", file=sys.stderr)
