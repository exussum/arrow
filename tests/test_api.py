import threading
from datetime import timedelta

import pytest

from arrow import api
from arrow.api import DeckManager
from arrow.config import config
from arrow.dal import orc
from arrow.dal.streamdeck import DisplayManager, ImageManager
from arrow.models import Dispatch

GIF = "countdowns/routines/fake.gif"
KEYS = (0, config.key_of("help"))
ICON = b"icon"
LABEL = b"label"
BLANK = b"blank"
FRAME = b"frame"
DELAYED = b"delayed"


class FakeDeck:
    def __init__(self):
        self.key_images = []
        self.brightness_calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def set_key_image(self, key, native):
        self.key_images.append((key, native))

    def set_brightness(self, level):
        self.brightness_calls.append(level)


def make_display_manager():
    deck = FakeDeck()
    cache = ImageManager(
        icons={k: ICON for k in KEYS},
        labels={k: LABEL for k in KEYS},
        frames={GIF: [FRAME]},
        blank={k: BLANK for k in KEYS},
        delayed={k: DELAYED for k in KEYS},
    )
    return DisplayManager(deck=deck, cache=cache), deck


@pytest.fixture
def make_manager():
    managers = []

    def _make(brightness=config.settings.dim_brightness):
        display, deck = make_display_manager()
        manager = DeckManager(brightness=brightness, display=display)
        managers.append(manager)
        return manager, deck

    yield _make
    for manager in managers:
        manager._cancel_dim()


def uploaded(deck):
    return [native for _, native in deck.key_images]


@pytest.mark.parametrize(
    ("seconds", "expected"),
    (
        (0, "0 seconds"),
        (1, "1 second"),
        (45, "45 seconds"),
        (60, "1 minute"),
        (90, "1 minute and 30 seconds"),
        (120, "2 minutes"),
    ),
)
def test_spoken_delay(seconds, expected):
    assert api._spoken_delay(timedelta(seconds=seconds)) == expected


class TestOnKeyChange:
    def test_ignores_release(self, make_manager):
        manager, deck = make_manager()
        manager.on_key_change(0, pressed=False)
        assert deck.key_images == []
        assert deck.brightness_calls == []

    def test_dim_wake_on_any_key(self, make_manager):
        manager, deck = make_manager(brightness=config.settings.dim_brightness)
        manager.on_key_change(3, pressed=True)
        assert manager._brightness == config.settings.active_brightness
        assert deck.brightness_calls == [config.settings.active_brightness]

    def test_help_key_toggles_labels(self, make_manager):
        manager, deck = make_manager(brightness=config.settings.active_brightness)
        manager.on_key_change(config.key_of("help"), pressed=True)
        assert uploaded(deck) == [LABEL] * len(KEYS)

    def test_dispatched_key_blanks_and_restores(self, make_manager):
        manager, deck = make_manager(brightness=config.settings.active_brightness)
        calls = []
        manager._dispatch = {5: Dispatch(gif=GIF, action=lambda: calls.append(5))}
        manager.on_key_change(5, pressed=True)
        assert uploaded(deck) == [BLANK] * len(KEYS) + [FRAME] + [ICON] * len(KEYS)
        assert calls == [5]

    def test_unmapped_key_prints_to_stderr(self, make_manager, capsys):
        manager, deck = make_manager(brightness=config.settings.active_brightness)
        manager._dispatch = {}
        manager.on_key_change(3, pressed=True)
        assert "3" in capsys.readouterr().err


class TestDim:
    def test_apply_dim_dims_when_active(self, make_manager):
        manager, deck = make_manager(brightness=config.settings.active_brightness)
        manager._dim_active = True
        manager._apply_dim()
        assert manager._brightness == config.settings.dim_brightness
        assert deck.brightness_calls == [config.settings.dim_brightness]

    def test_apply_dim_skips_when_cancelled(self, make_manager):
        manager, deck = make_manager(brightness=config.settings.active_brightness)
        manager._dim_active = False
        manager._apply_dim()
        assert manager._brightness == config.settings.active_brightness
        assert deck.brightness_calls == []

    def test_cancel_dim_stops_timer(self, make_manager):
        manager, _ = make_manager()
        timer = threading.Timer(60, lambda: None)
        timer.daemon = True
        timer.start()
        manager._dim_timer = timer
        manager._dim_active = True
        manager._cancel_dim()
        assert timer.finished.is_set()
        assert manager._dim_timer is None
        assert not manager._dim_active


class TestRun:
    def test_calls_action_and_restores_icons(self, make_manager):
        manager, deck = make_manager(brightness=config.settings.active_brightness)
        calls = []
        manager._run(0, GIF, lambda: calls.append(0))
        assert calls == [0]
        assert uploaded(deck)[-len(KEYS) :] == [ICON] * len(KEYS)

    def test_restores_icons_even_on_action_exception(self, make_manager):
        manager, deck = make_manager(brightness=config.settings.active_brightness)

        def action():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            manager._run(0, GIF, action)
        assert uploaded(deck)[-len(KEYS) :] == [ICON] * len(KEYS)

    def test_shows_delayed_notice_when_delay_present(self, make_manager, monkeypatch):
        manager, deck = make_manager(brightness=config.settings.active_brightness)
        monkeypatch.setattr(orc, "get_delay", lambda key: timedelta(minutes=3))
        sleeps, announced, calls = [], [], []
        monkeypatch.setattr(api.time, "sleep", sleeps.append)
        monkeypatch.setattr(orc, "call_announce", announced.append)
        manager._run(0, GIF, lambda: calls.append(0), "Goodnight", "AD_HOC_GOODNIGHT")
        assert deck.key_images[0] == (0, DELAYED)
        assert announced == ["Goodnight routine will go off in 3 minutes"]
        assert sleeps == [config.settings.delay_notice_seconds]
        assert calls == [0]

    def test_no_delayed_notice_when_no_delay(self, make_manager, monkeypatch):
        manager, deck = make_manager(brightness=config.settings.active_brightness)
        monkeypatch.setattr(orc, "get_delay", lambda key: None)
        manager._run(0, GIF, lambda: None, "Goodnight", "AD_HOC_GOODNIGHT")
        assert DELAYED not in uploaded(deck)

    def test_no_delayed_notice_without_a_delay_key(self, make_manager, monkeypatch):
        manager, deck = make_manager(brightness=config.settings.active_brightness)
        checked = []
        monkeypatch.setattr(orc, "get_delay", lambda key: checked.append(key) or timedelta(minutes=1))
        manager._run(0, GIF, lambda: None)
        assert checked == []
        assert DELAYED not in uploaded(deck)


class TestDisplayManagerLabels:
    def test_toggle_goes_to_labels_first(self):
        display, deck = make_display_manager()
        display.toggle_labels()
        assert display._show_labels is True
        assert uploaded(deck) == [LABEL] * len(KEYS)

    def test_toggle_returns_to_icons(self):
        display, deck = make_display_manager()
        display._show_labels = True
        display.toggle_labels()
        assert display._show_labels is False
        assert uploaded(deck) == [ICON] * len(KEYS)

    def test_on_dim_resets_labels(self):
        display, deck = make_display_manager()
        display._show_labels = True
        display.on_dim()
        assert display._show_labels is False
        assert uploaded(deck) == [ICON] * len(KEYS)

    def test_on_dim_noop_when_icons_showing(self):
        display, deck = make_display_manager()
        display._show_labels = False
        display.on_dim()
        assert deck.key_images == []
