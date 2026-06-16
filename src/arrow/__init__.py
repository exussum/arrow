from dataclasses import dataclass
from enum import Enum
from pathlib import Path

DIM_DELAY_SECONDS = 15
ACTIVE_BRIGHTNESS = 100
DIM_BRIGHTNESS = 0

ORC_BASE_URL = "http://remote.int.exussum.org"
HTTP_TIMEOUT = 60

ICONS_DIR = Path(__file__).resolve().parent / "icons"

PRESENCE_NAME = "me"


@dataclass(frozen=True)
class Button:
    slug: str
    display_name: str
    action: str


@dataclass(frozen=True)
class Routine:
    slug: str
    display_name: str


@dataclass(frozen=True)
class Other:
    slug: str
    display_name: str


class ButtonId(Enum):
    # name to position
    living_room_on     = 0
    living_room_off    = 1
    living_room_follow = 2
    kitchen_on         = 8
    kitchen_off        = 9
    kitchen_follow     = 10
    office_on          = 16
    office_off         = 17
    office_follow      = 18


class OtherId(Enum):
    # name to position
    presence = 7
    help     = 31


class RoutineId(Enum):
    # name to position
    bed_time             = 4
    partial_tv_lights    = 12
    tv_lights            = 20
    early_morning_lights = 28
    all_lights_on        = 5
    reset                = 13
    dog                  = 29
    silence              = 21
    up_and_atom          = 24
    sunset_lights        = 25
    back_on_schedule     = 26


BUTTONS: dict[ButtonId, Button] = {
    ButtonId.living_room_on:     Button("living_room", "Living Room", "on"),
    ButtonId.living_room_off:    Button("living_room", "Living Room", "off"),
    ButtonId.living_room_follow: Button("living_room", "Living Room", "follow"),
    ButtonId.kitchen_on:         Button("kitchen",     "Kitchen",     "on"),
    ButtonId.kitchen_off:        Button("kitchen",     "Kitchen",     "off"),
    ButtonId.kitchen_follow:     Button("kitchen",     "Kitchen",     "follow"),
    ButtonId.office_on:          Button("office",      "Office",      "on"),
    ButtonId.office_off:         Button("office",      "Office",      "off"),
    ButtonId.office_follow:      Button("office",      "Office",      "follow"),
}


ROUTINES: dict[RoutineId, Routine] = {
    RoutineId.bed_time:             Routine("bed_time",             "Bed Time"),
    RoutineId.partial_tv_lights:    Routine("partial_tv_lights",    "Partial TV Lights"),
    RoutineId.tv_lights:            Routine("tv_lights",            "TV Lights"),
    RoutineId.early_morning_lights: Routine("early_morning_lights", "Early Morning Lights"),
    RoutineId.all_lights_on:        Routine("all_lights_on",        "All Lights On"),
    RoutineId.reset:                Routine("reset",                "Reset"),
    RoutineId.dog:                  Routine("dog",                  "Dog"),
    RoutineId.silence:              Routine("silence",              "Silence"),
    RoutineId.up_and_atom:          Routine("up_and_atom",          "Up and Atom"),
    RoutineId.sunset_lights:        Routine("sunset_lights",        "Sunset Lights"),
    RoutineId.back_on_schedule:     Routine("back_on_schedule",     "Back on Schedule"),
}


OTHERS: dict[OtherId, Other] = {
    OtherId.help:     Other("help",     "Help"),
    OtherId.presence: Other("presence", "Check In"),
}


BUTTONS_BY_POSITION: dict[int, Button] = {bid.value: b for bid, b in BUTTONS.items()}
ROUTINES_BY_POSITION: dict[int, Routine] = {rid.value: r for rid, r in ROUTINES.items()}
OTHERS_BY_POSITION: dict[int, Other] = {oid.value: o for oid, o in OTHERS.items()}
