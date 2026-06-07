from pathlib import Path

DIM_DELAY_SECONDS = 60
ACTIVE_BRIGHTNESS = 100
DIM_BRIGHTNESS = 0

ORC_BASE_URL = "http://remote.int.exussum.example"
HTTP_TIMEOUT = 5

ICONS_DIR = Path(__file__).resolve().parent / "icons"

ROOM_TO_FILE = {
    "Hall": "hall",
    "Study": "study",
    "Garden": "garden",
    "Bedroom": "bedroom",
}

BUTTONS = {
    0: ("Hall", "on"),
    1: ("Hall", "off"),
    2: ("Hall", "follow"),
    8: ("Study", "on"),
    9: ("Study", "off"),
    10: ("Study", "follow"),
    16: ("Garden", "on"),
    17: ("Garden", "off"),
    18: ("Garden", "follow"),
    24: ("Bedroom", "on"),
    25: ("Bedroom", "off"),
    26: ("Bedroom", "follow"),
}

ROUTINES = {
    6:  "Goodnight",
    14: "Dim the Hall",
    22: "Movie Night",
    30: "Nightlights",
    7:  "Everything",
    15: "Everything Off",
    23: "Cat",
    31: "Hush",
}

ROUTINE_TO_FILE = {
    "Goodnight":             "goodnight",
    "Dim the Hall":    "dim_the_hall",
    "Movie Night":            "movie_night",
    "Nightlights": "nightlights",
    "Everything":        "everything",
    "Everything Off":       "everything_off",
    "Cat":                  "cat",
    "Hush":              "hush",
}
