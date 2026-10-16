import socket
import threading
from dataclasses import replace
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from arrow.config import config
from arrow.dal import orc


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    monkeypatch.setattr(orc, "_timings", lambda: {})


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
    monkeypatch.setattr(config, "settings", replace(config.settings, orc_base_url=f"http://127.0.0.1:{server.server_port}"))
    yield paths
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture
def unreachable_server(monkeypatch):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    monkeypatch.setattr(config, "settings", replace(config.settings, orc_base_url=f"http://127.0.0.1:{port}"))


class TestCallRoom:
    def test_builds_correct_url(self, received_paths):
        orc.call_room("hall", "on")
        assert received_paths == ["/api/room/hall?state=on"]

    def test_builds_url_for_each_state(self, received_paths):
        orc.call_room("garden", "follow")
        assert received_paths == ["/api/room/garden?state=follow"]

    def test_swallows_exceptions(self, unreachable_server, capsys):
        orc.call_room("study", "off")
        assert "call failed study off" in capsys.readouterr().err


class TestCallRoutine:
    def test_builds_correct_url(self, received_paths):
        orc.call_routine("goodnight", "Goodnight")
        assert received_paths == ["/api/run/goodnight"]

    def test_swallows_exceptions(self, unreachable_server, capsys):
        orc.call_routine("goodnight", "Goodnight")
        assert "call failed Goodnight" in capsys.readouterr().err


class TestCallPresence:
    def test_builds_correct_url(self, received_paths):
        orc.call_presence("someone")
        assert received_paths == ["/api/presence/someone/checkin"]

    def test_swallows_exceptions(self, unreachable_server, capsys):
        orc.call_presence("someone")
        assert "call failed presence someone" in capsys.readouterr().err


class TestGetDelay:
    def test_returns_delay_when_present(self, monkeypatch):
        monkeypatch.setattr(orc, "_timings", lambda: {"goodnight": {"delay": "0:03:00"}})
        assert orc.get_delay("goodnight") == timedelta(minutes=3)

    def test_returns_none_when_absent(self):
        assert orc.get_delay("goodnight") is None


def test_parse_delay():
    assert orc._parse_delay("0:03:00") == timedelta(minutes=3)
