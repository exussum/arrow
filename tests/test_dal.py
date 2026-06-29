from unittest.mock import patch

from arrow import dal


class TestCallRoom:
    @patch("arrow.dal.urllib.request.urlopen")
    def test_builds_correct_url(self, urlopen):
        dal.call_room("living_room", "on")
        assert urlopen.call_args[0][0] == "https://remote.int.exussum.org/api/room/living_room?state=on"

    @patch("arrow.dal.urllib.request.urlopen")
    def test_url_encodes_spaces(self, urlopen):
        dal.call_room("living room", "on")
        assert "living%20room" in urlopen.call_args[0][0]

    @patch("arrow.dal.urllib.request.urlopen", side_effect=Exception("timeout"))
    def test_swallows_exceptions(self, _):
        dal.call_room("living_room", "on")


class TestCallRoutine:
    @patch("arrow.dal.urllib.request.urlopen")
    def test_builds_correct_url(self, urlopen):
        dal.call_routine("bed_time")
        assert urlopen.call_args[0][0] == "https://remote.int.exussum.org/api/console/bed_time"

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
