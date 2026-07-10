import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from arrow import dal


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
        dal.call_room("hall", "on")
        assert received_paths == ["/api/room/hall?state=on"]

    def test_builds_url_for_each_state(self, received_paths):
        dal.call_room("garden", "follow")
        assert received_paths == ["/api/room/garden?state=follow"]

    def test_swallows_exceptions(self, unreachable_server, capsys):
        dal.call_room("study", "off")
        assert "call failed study off" in capsys.readouterr().err


class TestCallRoutine:
    def test_builds_correct_url(self, received_paths):
        dal.call_routine("goodnight")
        assert received_paths == ["/api/run/goodnight"]

    def test_swallows_exceptions(self, unreachable_server, capsys):
        dal.call_routine("goodnight")
        assert "call failed goodnight" in capsys.readouterr().err


class TestCallPresence:
    def test_builds_correct_url(self, received_paths):
        dal.call_presence("someone")
        assert received_paths == ["/api/presence/someone/checkin?ignore-version=1"]

    def test_swallows_exceptions(self, unreachable_server, capsys):
        dal.call_presence("someone")
        assert "call failed presence someone" in capsys.readouterr().err
