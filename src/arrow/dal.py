import functools
import json
import sys
import urllib.parse
import urllib.request
from datetime import timedelta

from arrow import HTTP_TIMEOUT, ORC_BASE_URL


def call_room(room: str, state: str) -> None:
    _announce_delay(room)
    url = f"{ORC_BASE_URL}/api/room/{urllib.parse.quote(room)}?state={urllib.parse.quote(state)}"
    try:
        urllib.request.urlopen(url, timeout=HTTP_TIMEOUT).close()
    except Exception as e:
        print(f"call failed {room} {state}: {e}", file=sys.stderr)


def call_routine(routine: str) -> None:
    _announce_delay(routine)
    url = f"{ORC_BASE_URL}/api/run/{urllib.parse.quote(routine)}"
    try:
        urllib.request.urlopen(url, timeout=HTTP_TIMEOUT).close()
    except Exception as e:
        print(f"call failed {routine}: {e}", file=sys.stderr)


def call_presence(name: str) -> None:
    url = f"{ORC_BASE_URL}/api/presence/{urllib.parse.quote(name)}/checkin?ignore-version=1"
    try:
        urllib.request.urlopen(url, timeout=HTTP_TIMEOUT).close()
    except Exception as e:
        print(f"call failed presence {name}: {e}", file=sys.stderr)


def call_announce(text: str) -> None:
    url = f"{ORC_BASE_URL}/api/announce?ignore-version=1"
    data = urllib.parse.urlencode({"text": text}).encode()
    try:
        urllib.request.urlopen(url, data=data, timeout=HTTP_TIMEOUT).close()
    except Exception as e:
        print(f"call failed announce {text}: {e}", file=sys.stderr)


@functools.cache
def _delays() -> dict[str, timedelta]:
    url = f"{ORC_BASE_URL}/api/durations"
    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT) as r:
            data = json.load(r)
    except Exception as e:
        print(f"fetch failed durations: {e}", file=sys.stderr)
        return {}
    return {name: _parse_delay(entry["delay"]) for name, entry in data.items()}


def _parse_delay(value: str) -> timedelta:
    hours, minutes, seconds = value.split(":")
    return timedelta(hours=int(hours), minutes=int(minutes), seconds=float(seconds))


def _announce_delay(name: str) -> None:
    if delay := _delays().get(name):
        call_announce(f"{name} routine will go off in {_format_delay(delay)}")


def _format_delay(delta: timedelta) -> str:
    minutes, seconds = divmod(int(delta.total_seconds()), 60)
    parts = []
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return " and ".join(parts)
