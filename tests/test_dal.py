from unittest.mock import patch

from arrow import dal


class TestCallRoom:
    @patch("arrow.dal.urllib.request.urlopen")
    def test_builds_correct_url(self, urlopen):
        dal.call_room("hall", "on")
        assert urlopen.call_args[0][0] == "https://remote.int.exussum.example/api/room/hall?state=on"

    @patch("arrow.dal.urllib.request.urlopen")
    def test_builds_url_for_each_state(self, urlopen):
        dal.call_room("garden", "follow")
        assert urlopen.call_args[0][0] == "https://remote.int.exussum.example/api/room/garden?state=follow"

    @patch("arrow.dal.urllib.request.urlopen", side_effect=Exception("timeout"))
    def test_swallows_exceptions(self, _):
        dal.call_room("study", "off")


class TestCallRoutine:
    @patch("arrow.dal.urllib.request.urlopen")
    def test_builds_correct_url(self, urlopen):
        dal.call_routine("goodnight")
        assert urlopen.call_args[0][0] == "https://remote.int.exussum.example/api/run/goodnight"

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
