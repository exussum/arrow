from enum import Enum
from pathlib import Path

from arrow.models import Button, Other, Routine

DIM_DELAY_SECONDS = 15
ACTIVE_BRIGHTNESS = 100
DIM_BRIGHTNESS = 0

ORC_BASE_URL = "https://remote.int.exussum.example"
HTTP_TIMEOUT = 60

ICONS_DIR = Path(__file__).resolve().parent / "icons"

PRESENCE_NAME = "someone"


class ButtonId(Enum):
    # name to position
    hall_on = 0
    hall_off = 1
    hall_follow = 2
    garden_on = 8
    garden_off = 9
    garden_follow = 10
    study_on = 16
    study_off = 17
    study_follow = 18


class OtherId(Enum):
    # name to position
    presence = 7
    help = 31


class RoutineId(Enum):
    # name to position
    goodnight = 4
    dim_the_hall = 12
    movie_night = 20
    nightlights = 28
    everything = 5
    reset = 13
    cat = 29
    hush = 21
    wake_up = 24
    dusk = 25
    weekly_review = 26


BUTTONS: dict[ButtonId, Button] = {
    ButtonId.hall_on: Button("hall", "Hall", "on"),
    ButtonId.hall_off: Button("hall", "Hall", "off"),
    ButtonId.hall_follow: Button("hall", "Hall", "follow"),
    ButtonId.garden_on: Button("garden", "Garden", "on"),
    ButtonId.garden_off: Button("garden", "Garden", "off"),
    ButtonId.garden_follow: Button("garden", "Garden", "follow"),
    ButtonId.study_on: Button("study", "Study", "on"),
    ButtonId.study_off: Button("study", "Study", "off"),
    ButtonId.study_follow: Button("study", "Study", "follow"),
}


ROUTINES: dict[RoutineId, Routine] = {
    RoutineId.goodnight: Routine("goodnight", "Goodnight"),
    RoutineId.dim_the_hall: Routine("dim_the_hall", "Dim the Hall"),
    RoutineId.movie_night: Routine("movie_night", "Movie Night"),
    RoutineId.nightlights: Routine("nightlights", "Nightlights"),
    RoutineId.everything: Routine("everything", "Everything"),
    RoutineId.reset: Routine("reset", "Reset"),
    RoutineId.cat: Routine("cat", "Cat"),
    RoutineId.hush: Routine("hush", "Hush"),
    RoutineId.wake_up: Routine("wake_up", "Wake Up"),
    RoutineId.dusk: Routine("dusk", "Dusk"),
    RoutineId.weekly_review: Routine("weekly_review", "Weekly Review"),
}


OTHERS: dict[OtherId, Other] = {
    OtherId.help: Other("help", "Help"),
    OtherId.presence: Other("presence", "Check In"),
}


BUTTONS_BY_POSITION: dict[int, Button] = {bid.value: b for bid, b in BUTTONS.items()}
ROUTINES_BY_POSITION: dict[int, Routine] = {rid.value: r for rid, r in ROUTINES.items()}
OTHERS_BY_POSITION: dict[int, Other] = {oid.value: o for oid, o in OTHERS.items()}
