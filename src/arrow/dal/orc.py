import functools
import sys
from datetime import timedelta
from typing import Any
from urllib.parse import quote

import requests

from arrow.config import config


def _url(path: str) -> str:
    return f"{config.settings.orc_base_url}{path}"


def _send(url: str, label: str, data: dict[str, str] | None = None) -> None:
    try:
        timeout = config.settings.http_timeout
        response = requests.post(url, data=data, timeout=timeout) if data else requests.get(url, timeout=timeout)
        response.raise_for_status()
    except Exception as e:
        print(f"call failed {label}: {e!r}", file=sys.stderr)


def _fetch(path: str, label: str) -> Any | None:
    try:
        response = requests.get(_url(path), timeout=config.settings.http_timeout)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"fetch failed {label}: {e}", file=sys.stderr)
        return None


def call_room(room: str, state: str) -> None:
    _announce_delay(room, room)
    _send(_url(f"/api/room/{quote(room)}?state={quote(state)}"), f"{room} {state}")


def call_routine(routine: str, name: str) -> None:
    _announce_delay(routine, name)
    _send(_url(f"/api/run/{quote(routine)}"), name)


def call_presence(name: str) -> None:
    _send(_url(f"/api/presence/{quote(name)}/checkin"), f"presence {name}")


def call_announce(text: str) -> None:
    _send(_url("/api/announce"), f"announce {text}", data={"text": text})


def fetch_actions() -> dict[str, Any] | None:
    return _fetch("/api/actions", "actions")


def fetch_durations() -> dict[str, int]:
    data = _fetch("/api/durations", "durations") or {}
    return {name: int(sample["avg"]) for name, sample in data.items()}


@functools.cache
def _delays() -> dict[str, timedelta]:
    data = _fetch("/api/durations", "durations") or {}
    return {name: _parse_delay(entry["delay"]) for name, entry in data.items()}


def _parse_delay(value: str) -> timedelta:
    hours, minutes, seconds = value.split(":")
    return timedelta(hours=int(hours), minutes=int(minutes), seconds=float(seconds))


def get_delay(name: str) -> timedelta | None:
    return _delays().get(name)


def _announce_delay(routine: str, name: str) -> None:
    if delay := get_delay(routine):
        call_announce(f"{name} routine will go off in {_format_delay(delay)}")


def _format_delay(delta: timedelta) -> str:
    minutes, seconds = divmod(int(delta.total_seconds()), 60)
    parts = []
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return " and ".join(parts)
