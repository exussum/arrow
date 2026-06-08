from dataclasses import dataclass
from enum import Enum
from pathlib import Path

DIM_DELAY_SECONDS = 30
ACTIVE_BRIGHTNESS = 100
DIM_BRIGHTNESS = 0

ORC_BASE_URL = "http://remote.int.exussum.example"
HTTP_TIMEOUT = 120

ICONS_DIR = Path(__file__).resolve().parent / "icons"


@dataclass(frozen=True)
class Button:
    slug: str
    display_name: str
    action: str


@dataclass(frozen=True)
class Routine:
    slug: str
    display_name: str


class ButtonId(Enum):
    # name to position
    hall_on     = 0
    hall_off    = 1
    hall_follow = 2
    garden_on         = 8
    garden_off        = 9
    garden_follow     = 10
    study_on          = 16
    study_off         = 17
    study_follow      = 18


class RoutineId(Enum):
    # name to position
    goodnight             = 6
    dim_the_hall    = 14
    movie_night            = 22
    nightlights = 30
    everything        = 7
    reset                = 15
    cat                  = 31
    hush              = 23
    wake_up          = 24
    dusk        = 25
    weekly_review     = 26


BUTTONS: dict[ButtonId, Button] = {
    ButtonId.hall_on:     Button("hall", "Hall", "on"),
    ButtonId.hall_off:    Button("hall", "Hall", "off"),
    ButtonId.hall_follow: Button("hall", "Hall", "follow"),
    ButtonId.garden_on:         Button("garden",     "Garden",     "on"),
    ButtonId.garden_off:        Button("garden",     "Garden",     "off"),
    ButtonId.garden_follow:     Button("garden",     "Garden",     "follow"),
    ButtonId.study_on:          Button("study",      "Study",      "on"),
    ButtonId.study_off:         Button("study",      "Study",      "off"),
    ButtonId.study_follow:      Button("study",      "Study",      "follow"),
}


ROUTINES: dict[RoutineId, Routine] = {
    RoutineId.goodnight:             Routine("goodnight",             "Goodnight"),
    RoutineId.dim_the_hall:    Routine("dim_the_hall",    "Dim the Hall"),
    RoutineId.movie_night:            Routine("movie_night",            "Movie Night"),
    RoutineId.nightlights: Routine("nightlights", "Nightlights"),
    RoutineId.everything:        Routine("everything",        "Everything"),
    RoutineId.reset:                Routine("reset",                "Reset"),
    RoutineId.cat:                  Routine("cat",                  "Cat"),
    RoutineId.hush:              Routine("hush",              "Hush"),
    RoutineId.wake_up:          Routine("wake_up",          "Wake Up"),
    RoutineId.dusk:        Routine("dusk",        "Dusk"),
    RoutineId.weekly_review:     Routine("weekly_review",     "Weekly Review"),
}


BUTTONS_BY_POSITION: dict[int, Button] = {bid.value: b for bid, b in BUTTONS.items()}
ROUTINES_BY_POSITION: dict[int, Routine] = {rid.value: r for rid, r in ROUTINES.items()}
