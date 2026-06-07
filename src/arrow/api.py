import sys
import threading
from datetime import datetime, timedelta

from PIL import Image
from StreamDeck.ImageHelpers import PILHelper

from arrow import (
    ACTIVE_BRIGHTNESS,
    BUTTONS,
    DIM_BRIGHTNESS,
    DIM_DELAY_SECONDS,
    ICONS_DIR,
    ROOM_TO_FILE,
    ROUTINE_TO_FILE,
    ROUTINES,
)
from arrow import dal


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
        current = state.brightness

    if current == DIM_BRIGHTNESS:
        apply_brightness(deck, state, ACTIVE_BRIGHTNESS)
        scheduler.add_job(
            apply_brightness,
            "date",
            run_date=datetime.now() + timedelta(seconds=DIM_DELAY_SECONDS),
            args=[deck, state, DIM_BRIGHTNESS],
            id="dim",
            replace_existing=True,
        )
        return

    if key in BUTTONS:
        room, room_state = BUTTONS[key]
        dal.call_room(room, room_state)
    elif key in ROUTINES:
        dal.call_routine(ROUTINES[key])
    else:
        print(f"button {key} unmapped", file=sys.stderr)


def upload_icons(deck):
    targets = []
    for key, (room, action) in BUTTONS.items():
        targets.append((key, ICONS_DIR / action / f"{ROOM_TO_FILE[room]}.png", f"{room} {action}"))
    for key, routine in ROUTINES.items():
        targets.append((key, ICONS_DIR / "routines" / f"{ROUTINE_TO_FILE[routine]}.png", routine))

    total = len(targets)
    for i, (key, path, label) in enumerate(targets, 1):
        if not path.exists():
            print(f"[{i}/{total}] missing icon {path}", file=sys.stderr)
            continue
        with Image.open(path) as img:
            scaled = PILHelper.create_scaled_image(deck, img, margins=[0, 0, 0, 0])
        native = PILHelper.to_native_format(deck, scaled)
        with deck:
            deck.set_key_image(key, native)
    print(f"uploaded {total} icons", file=sys.stderr)
