import socket
import threading
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from arrow import dal


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    monkeypatch.setattr(dal, "_delays", lambda: {})


@pytest.fixture
def received_paths(monkeypatch):
    paths = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            paths.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(dal, "ORC_BASE_URL", f"http://127.0.0.1:{server.server_port}")
    yield paths
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture
def unreachable_server(monkeypatch):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    monkeypatch.setattr(dal, "ORC_BASE_URL", f"http://127.0.0.1:{port}")


class TestCallRoom:
    def test_builds_correct_url(self, received_paths):
        dal.call_room("living_room", "on")
        assert received_paths == ["/api/room/living_room?state=on"]

    def test_builds_url_for_each_state(self, received_paths):
        dal.call_room("kitchen", "follow")
        assert received_paths == ["/api/room/kitchen?state=follow"]

    def test_swallows_exceptions(self, unreachable_server, capsys):
        dal.call_room("office", "off")
        assert "call failed office off" in capsys.readouterr().err


class TestCallRoutine:
    def test_builds_correct_url(self, received_paths):
        dal.call_routine("bed_time")
        assert received_paths == ["/api/run/bed_time"]

    def test_swallows_exceptions(self, unreachable_server, capsys):
        dal.call_routine("bed_time")
        assert "call failed bed_time" in capsys.readouterr().err


class TestCallPresence:
    def test_builds_correct_url(self, received_paths):
        dal.call_presence("me")
        assert received_paths == ["/api/presence/me/checkin?ignore-version=1"]

    def test_swallows_exceptions(self, unreachable_server, capsys):
        dal.call_presence("me")
        assert "call failed presence me" in capsys.readouterr().err


class TestAnnounceDelay:
    def test_announces_before_calling_when_delay_present(self, monkeypatch, received_paths):
        monkeypatch.setattr(dal, "_delays", lambda: {"bed_time": timedelta(minutes=3)})
        announced = []
        monkeypatch.setattr(dal, "call_announce", announced.append)
        dal.call_routine("bed_time")
        assert announced == ["bed_time routine will go off in 3 minutes"]
        assert received_paths == ["/api/run/bed_time"]

    def test_no_announcement_when_no_delay(self, monkeypatch, received_paths):
        announced = []
        monkeypatch.setattr(dal, "call_announce", announced.append)
        dal.call_room("living_room", "on")
        assert announced == []


class TestGetDelay:
    def test_returns_delay_when_present(self, monkeypatch):
        monkeypatch.setattr(dal, "_delays", lambda: {"bed_time": timedelta(minutes=3)})
        assert dal.get_delay("bed_time") == timedelta(minutes=3)

    def test_returns_none_when_absent(self):
        assert dal.get_delay("bed_time") is None


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (0, "0 seconds"),
        (1, "1 second"),
        (45, "45 seconds"),
        (60, "1 minute"),
        (90, "1 minute and 30 seconds"),
        (120, "2 minutes"),
    ],
)
def test_format_delay(seconds, expected):
    assert dal._format_delay(timedelta(seconds=seconds)) == expected


def test_parse_delay():
    assert dal._parse_delay("0:03:00") == timedelta(minutes=3)
