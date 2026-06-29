from unittest.mock import patch

from arrow import dal


class TestCallRoutine:
    @patch("arrow.dal.urllib.request.urlopen")
    def test_builds_correct_url(self, urlopen):
        dal.call_routine("bed_time")
        assert urlopen.call_args[0][0] == "https://remote.int.exussum.org/api/console/bed_time"

    @patch("arrow.dal.urllib.request.urlopen")
    def test_room_action_uses_console_endpoint(self, urlopen):
        dal.call_routine("living_room_on")
        assert urlopen.call_args[0][0] == "https://remote.int.exussum.org/api/console/living_room_on"

    @patch("arrow.dal.urllib.request.urlopen", side_effect=Exception("timeout"))
    def test_swallows_exceptions(self, _):
        dal.call_routine("bed_time")


class TestCallPresence:
    @patch("arrow.dal.urllib.request.urlopen")
    def test_builds_correct_url(self, urlopen):
        dal.call_presence("me")
        assert urlopen.call_args[0][0] == "https://remote.int.exussum.org/api/presence/me/checkin?ignore-version=1"

    @patch("arrow.dal.urllib.request.urlopen", side_effect=Exception("timeout"))
    def test_swallows_exceptions(self, _):
        dal.call_presence("me")
