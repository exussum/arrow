from pathlib import Path
from unittest.mock import MagicMock, call, patch

from arrow import ACTIVE_BRIGHTNESS, DIM_BRIGHTNESS, OtherId
from arrow.api import DeckManager, DisplayManager
from arrow.models import Dispatch, IconMode


def make_deck_manager(brightness=DIM_BRIGHTNESS):
    display = MagicMock()
    return DeckManager(brightness=brightness, display=display), display


def make_display_manager():
    deck = MagicMock()
    cache = MagicMock()
    cache.icons = {}
    cache.labels = {}
    cache.blank = {}
    return DisplayManager(deck=deck, cache=cache), deck


class TestOnKeyChange:
    def test_ignores_release(self):
        manager, display = make_deck_manager()
        manager.on_key_change(0, pressed=False)
        display.upload_icons.assert_not_called()

    @patch("threading.Timer")
    def test_dim_wake_on_any_key(self, _timer):
        manager, display = make_deck_manager(brightness=DIM_BRIGHTNESS)
        manager.on_key_change(3, pressed=True)
        assert manager._brightness == ACTIVE_BRIGHTNESS

    @patch("threading.Timer")
    def test_help_key_toggles_labels(self, _timer):
        manager, display = make_deck_manager(brightness=ACTIVE_BRIGHTNESS)
        manager.on_key_change(OtherId.help.value, pressed=True)
        display.toggle_labels.assert_called_once()

    @patch("threading.Timer")
    def test_dispatched_key_blanks_and_restores(self, _timer):
        manager, display = make_deck_manager(brightness=ACTIVE_BRIGHTNESS)
        action = MagicMock()
        manager._DISPATCH = {5: Dispatch(gif=Path("/fake/countdown.gif"), action=action)}
        manager.on_key_change(5, pressed=True)
        assert display.upload_icons.call_args_list == [call(IconMode.BLANK), call(IconMode.ICONS)]
        action.assert_called_once()

    @patch("threading.Timer")
    def test_unmapped_key_prints_to_stderr(self, _timer, capsys):
        manager, display = make_deck_manager(brightness=ACTIVE_BRIGHTNESS)
        manager._DISPATCH = {}
        manager.on_key_change(3, pressed=True)
        assert "3" in capsys.readouterr().err


class TestDim:
    def test_apply_dim_dims_when_active(self):
        manager, display = make_deck_manager(brightness=ACTIVE_BRIGHTNESS)
        manager._dim_active = True
        manager._apply_dim()
        assert manager._brightness == DIM_BRIGHTNESS

    def test_apply_dim_skips_when_cancelled(self):
        manager, display = make_deck_manager(brightness=ACTIVE_BRIGHTNESS)
        manager._dim_active = False
        manager._apply_dim()
        assert manager._brightness == ACTIVE_BRIGHTNESS

    def test_cancel_dim_stops_timer(self):
        manager, display = make_deck_manager()
        mock_timer = MagicMock()
        manager._dim_timer = mock_timer
        manager._dim_active = True
        manager._cancel_dim()
        mock_timer.cancel.assert_called_once()
        assert not manager._dim_active


class TestRun:
    @patch("threading.Timer")
    def test_calls_action_and_restores_icons(self, _timer):
        manager, display = make_deck_manager(brightness=ACTIVE_BRIGHTNESS)
        action = MagicMock()
        manager._run(0, Path("/fake/countdown.gif"), action)
        action.assert_called_once()
        display.upload_icons.assert_called_with(IconMode.ICONS)

    @patch("threading.Timer")
    def test_restores_icons_even_on_action_exception(self, _timer):
        manager, display = make_deck_manager(brightness=ACTIVE_BRIGHTNESS)
        action = MagicMock(side_effect=RuntimeError("boom"))
        try:
            manager._run(0, Path("/fake/countdown.gif"), action)
        except RuntimeError:
            pass
        display.upload_icons.assert_called_with(IconMode.ICONS)


class TestDisplayManagerLabels:
    def test_toggle_goes_to_labels_first(self):
        display, _ = make_display_manager()
        display.toggle_labels()
        assert display._show_labels is True

    def test_toggle_returns_to_icons(self):
        display, _ = make_display_manager()
        display._show_labels = True
        display.toggle_labels()
        assert display._show_labels is False

    def test_on_dim_resets_labels(self):
        display, _ = make_display_manager()
        display._show_labels = True
        display.on_dim()
        assert display._show_labels is False

    def test_on_dim_noop_when_icons_showing(self):
        display, deck = make_display_manager()
        display._show_labels = False
        display.on_dim()
        deck.set_key_image.assert_not_called()
