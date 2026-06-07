from pathlib import Path

DIM_DELAY_SECONDS = 60
ACTIVE_BRIGHTNESS = 100
DIM_BRIGHTNESS = 0

ORC_BASE_URL = "http://remote.int.exussum.org"
HTTP_TIMEOUT = 5

ICONS_DIR = Path(__file__).resolve().parent / "icons"

ROOM_TO_FILE = {
    "Living Room": "living_room",
    "Office": "office",
    "Kitchen": "kitchen",
    "Bedroom": "bedroom",
}

BUTTONS = {
    0: ("Living Room", "on"),
    1: ("Living Room", "off"),
    2: ("Living Room", "follow"),
    8: ("Office", "on"),
    9: ("Office", "off"),
    10: ("Office", "follow"),
    16: ("Kitchen", "on"),
    17: ("Kitchen", "off"),
    18: ("Kitchen", "follow"),
    24: ("Bedroom", "on"),
    25: ("Bedroom", "off"),
    26: ("Bedroom", "follow"),
}

ROUTINES = {
    6:  "Bed Time",
    14: "Partial TV Lights",
    22: "TV Lights",
    30: "Early Morning Lights",
    7:  "All Lights On",
    15: "All Lights Off",
    23: "Dog",
    31: "Silence",
}

ROUTINE_TO_FILE = {
    "Bed Time":             "bed_time",
    "Partial TV Lights":    "partial_tv_lights",
    "TV Lights":            "tv_lights",
    "Early Morning Lights": "early_morning_lights",
    "All Lights On":        "all_lights_on",
    "All Lights Off":       "all_lights_off",
    "Dog":                  "dog",
    "Silence":              "silence",
}
