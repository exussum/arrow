from pathlib import Path

import pytest
from command_cfg import ConfigError

from arrow.loader import Icon, parse

FIXTURES = Path(__file__).parent / "fixture"


def parsed(name: str = "base"):
    return parse((FIXTURES / f"{name}.arrow").read_text())


@pytest.mark.parametrize(
    ("fixture", "expected"),
    (
        ("duplicate_key", "key 4 is claimed twice"),
        ("unknown_button_slug", "matches no room, routine or other"),
        ("room_without_state", "needs one of"),
        ("non_room_with_state", "takes no action"),
        ("unknown_icon_filter", "unknown icon filter"),
    ),
)
def test_rejects(fixture, expected):
    with pytest.raises(ConfigError, match=expected):
        parsed(fixture)


def test_rooms_expand_to_one_button_per_state():
    config = parsed()
    assert {button.action for button in config.buttons.values()} == {"on", "off", "follow"}
    assert all(button.display_name == "Den" for button in config.buttons.values())


def test_orc_id_defaults_to_ad_hoc_slug():
    routines = {routine.slug: routine.orc_id for routine in parsed().routines.values()}
    assert routines == {"nap": "AD_HOC_NAP", "reset": "ROUTINE_RESET", "lights": "AD_HOC_LIGHTS"}


@pytest.mark.parametrize(
    ("key", "expected"),
    (
        ("nap", (Icon("sleeping-symbol"),)),
        ("reset", (Icon("electric-light-bulb", "dim"), Icon("speaker-with-cancellation-stroke"))),
        ("den/off", (Icon("couch-and-lamp"),)),
    ),
)
def test_layouts_become_art(key, expected):
    assert parsed().art[key].icons == expected


def test_caption_and_badge_land_on_art():
    config = parsed()
    assert config.art["lights"].text == "All lights"
    assert config.art["den/off"].badge == Icon("electric-light-bulb", "dim")


def test_icon_names_resolve_to_glyphs():
    assert Icon("electric-light-bulb").char == "\U0001f4a1"
    with pytest.raises(ConfigError, match="unknown icon name"):
        Icon("not-an-emoji").char
