from unittest.mock import patch

from arrow import dal


class TestCallRoutine:
    @patch("arrow.dal.urllib.request.urlopen")
    def test_builds_correct_url(self, urlopen):
        dal.call_routine("goodnight")
        assert urlopen.call_args[0][0] == "https://remote.int.exussum.example/api/run/goodnight"

    @patch("arrow.dal.urllib.request.urlopen")
    def test_room_action_uses_run_endpoint(self, urlopen):
        dal.call_routine("hall_on")
        assert urlopen.call_args[0][0] == "https://remote.int.exussum.example/api/run/hall_on"

    @patch("arrow.dal.urllib.request.urlopen", side_effect=Exception("timeout"))
    def test_swallows_exceptions(self, _):
        dal.call_routine("goodnight")


class TestCallPresence:
    @patch("arrow.dal.urllib.request.urlopen")
    def test_builds_correct_url(self, urlopen):
        dal.call_presence("someone")
        assert urlopen.call_args[0][0] == "https://remote.int.exussum.example/api/presence/someone/checkin?ignore-version=1"

    @patch("arrow.dal.urllib.request.urlopen", side_effect=Exception("timeout"))
    def test_swallows_exceptions(self, _):
        dal.call_presence("someone")
