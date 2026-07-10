import threading
from pathlib import Path

import pytest

from arrow import ACTIVE_BRIGHTNESS, DIM_BRIGHTNESS, OtherId
from arrow.api import DeckManager, DisplayManager, ImageManager
from arrow.models import Dispatch

GIF = Path("/fake/countdown.gif")
KEYS = (0, OtherId.help.value)
ICON = b"icon"
LABEL = b"label"
BLANK = b"blank"
FRAME = b"frame"


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
    )
    return DisplayManager(deck=deck, cache=cache), deck


@pytest.fixture
def make_manager():
    managers = []

    def _make(brightness=DIM_BRIGHTNESS):
        display, deck = make_display_manager()
        manager = DeckManager(brightness=brightness, display=display)
        managers.append(manager)
        return manager, deck

    yield _make
    for manager in managers:
        manager._cancel_dim()


def uploaded(deck):
    return [native for _, native in deck.key_images]


class TestOnKeyChange:
    def test_ignores_release(self, make_manager):
        manager, deck = make_manager()
        manager.on_key_change(0, pressed=False)
        assert deck.key_images == []
        assert deck.brightness_calls == []

    def test_dim_wake_on_any_key(self, make_manager):
        manager, deck = make_manager(brightness=DIM_BRIGHTNESS)
        manager.on_key_change(3, pressed=True)
        assert manager._brightness == ACTIVE_BRIGHTNESS
        assert deck.brightness_calls == [ACTIVE_BRIGHTNESS]

    def test_help_key_toggles_labels(self, make_manager):
        manager, deck = make_manager(brightness=ACTIVE_BRIGHTNESS)
        manager.on_key_change(OtherId.help.value, pressed=True)
        assert uploaded(deck) == [LABEL] * len(KEYS)

    def test_dispatched_key_blanks_and_restores(self, make_manager):
        manager, deck = make_manager(brightness=ACTIVE_BRIGHTNESS)
        calls = []
        manager._DISPATCH = {5: Dispatch(gif=GIF, action=lambda: calls.append(5))}
        manager.on_key_change(5, pressed=True)
        assert uploaded(deck) == [BLANK] * len(KEYS) + [FRAME] + [ICON] * len(KEYS)
        assert calls == [5]

    def test_unmapped_key_prints_to_stderr(self, make_manager, capsys):
        manager, deck = make_manager(brightness=ACTIVE_BRIGHTNESS)
        manager._DISPATCH = {}
        manager.on_key_change(3, pressed=True)
        assert "3" in capsys.readouterr().err


class TestDim:
    def test_apply_dim_dims_when_active(self, make_manager):
        manager, deck = make_manager(brightness=ACTIVE_BRIGHTNESS)
        manager._dim_active = True
        manager._apply_dim()
        assert manager._brightness == DIM_BRIGHTNESS
        assert deck.brightness_calls == [DIM_BRIGHTNESS]

    def test_apply_dim_skips_when_cancelled(self, make_manager):
        manager, deck = make_manager(brightness=ACTIVE_BRIGHTNESS)
        manager._dim_active = False
        manager._apply_dim()
        assert manager._brightness == ACTIVE_BRIGHTNESS
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
        manager, deck = make_manager(brightness=ACTIVE_BRIGHTNESS)
        calls = []
        manager._run(0, GIF, lambda: calls.append(0))
        assert calls == [0]
        assert uploaded(deck)[-len(KEYS) :] == [ICON] * len(KEYS)

    def test_restores_icons_even_on_action_exception(self, make_manager):
        manager, deck = make_manager(brightness=ACTIVE_BRIGHTNESS)

        def action():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            manager._run(0, GIF, action)
        assert uploaded(deck)[-len(KEYS) :] == [ICON] * len(KEYS)


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
