from pathlib import Path

import pytest
from command_cfg import ConfigError

from arrow.loader import Caption, Icon, Marked, Pair, Single, parse

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
        ("unknown_icon_name", "unknown icon name"),
        ("missing_badge", "missing off, follow"),
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
        ("nap", Single(Icon("\U0001f4a4"))),
        ("reset", Pair(Icon("\U0001f4a1", "dim"), Icon("\U0001f507"))),
        ("lights", Caption(Icon("\U0001f4a1"), "All lights")),
        ("den/off", Marked(Icon("\U0001f6cb"), Icon("\U0001f4a1", "dim"))),
    ),
)
def test_layouts_become_art(key, expected):
    assert parsed().art[key] == expected
