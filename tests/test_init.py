import pytest
from command_cfg import ConfigError

from arrow.loader import Icon, parse

BASE = """
setting orc_base_url  http://orc.example
setting presence_name someone

badge on     electric-light-bulb
badge off    electric-light-bulb:dim
badge follow pushpin

room den Den couch-and-lamp

routine single  nap     Nap       sleeping-symbol
routine pair    reset   Reset     electric-light-bulb:dim speaker-with-cancellation-stroke --orc-id=ROUTINE_RESET
routine caption lights 'Lights'   electric-light-bulb     'All lights'

other help Help black-question-mark-ornament
"""


def config(buttons):
    return parse(BASE + buttons)


def test_rooms_expand_to_one_button_per_state():
    c = config("button den on 0\nbutton den off 1\nbutton den follow 2\n")
    assert {b.action for b in c.buttons.values()} == {"on", "off", "follow"}
    assert all(b.display_name == "Den" for b in c.buttons.values())


def test_orc_id_defaults_to_ad_hoc_slug():
    c = config("button nap 4\nbutton reset 5\n")
    assert {r.slug: r.orc_id for r in c.routines.values()} == {"nap": "AD_HOC_NAP", "reset": "ROUTINE_RESET"}


def test_duplicate_key_is_rejected():
    with pytest.raises(ConfigError, match="key 4 is claimed twice"):
        config("button nap 4\nbutton help 4\n")


def test_unknown_slug_is_rejected():
    with pytest.raises(ConfigError, match="matches no room, routine or other"):
        config("button nothing 4\n")


def test_room_button_needs_a_state():
    with pytest.raises(ConfigError, match="needs one of"):
        config("button den 0\n")


def test_non_room_button_rejects_a_state():
    with pytest.raises(ConfigError, match="takes no action"):
        config("button nap on 4\n")


def test_layouts_become_art():
    c = config("button nap 4\nbutton reset 5\nbutton lights 6\nbutton den on 0\n")
    assert c.art["nap"].icons == (Icon("sleeping-symbol"),)
    assert c.art["reset"].icons == (Icon("electric-light-bulb", "dim"), Icon("speaker-with-cancellation-stroke"))
    assert c.art["lights"].text == "All lights"
    assert c.art["den/off"].badge == Icon("electric-light-bulb", "dim")


def test_icon_names_resolve_to_glyphs():
    assert Icon("electric-light-bulb").char == "\U0001f4a1"
    with pytest.raises(ConfigError, match="unknown icon name"):
        Icon("not-an-emoji").char
    with pytest.raises(ConfigError, match="unknown icon filter"):
        Icon.parse("electric-light-bulb:sideways")
