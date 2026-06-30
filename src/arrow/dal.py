import sys
import urllib.parse
import urllib.request

from arrow import HTTP_TIMEOUT, ORC_BASE_URL


def call_room(room, state):
    url = f"{ORC_BASE_URL}/api/room/{urllib.parse.quote(room)}?state={urllib.parse.quote(state)}"
    try:
        urllib.request.urlopen(url, timeout=HTTP_TIMEOUT).close()
    except Exception as e:
        print(f"call failed {room} {state}: {e}", file=sys.stderr)


def call_routine(routine):
    url = f"{ORC_BASE_URL}/api/run/{urllib.parse.quote(routine)}"
    try:
        urllib.request.urlopen(url, timeout=HTTP_TIMEOUT).close()
    except Exception as e:
        print(f"call failed {routine}: {e}", file=sys.stderr)


def call_presence(name):
    url = f"{ORC_BASE_URL}/api/presence/{urllib.parse.quote(name)}/checkin?ignore-version=1"
    try:
        urllib.request.urlopen(url, timeout=HTTP_TIMEOUT).close()
    except Exception as e:
        print(f"call failed presence {name}: {e}", file=sys.stderr)
