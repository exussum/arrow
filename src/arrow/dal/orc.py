import functools
import sys
from datetime import timedelta
from typing import Any
from urllib.parse import quote, urljoin

import requests

from arrow.config import config


def call_room(room: str, state: str) -> None:
    _send(_url(f"/api/room/{quote(room)}?state={quote(state)}"), f"{room} {state}")


def call_routine(routine: str, name: str) -> None:
    _send(_url(f"/api/run/{quote(routine)}"), name)


def call_presence(name: str) -> None:
    _send(_url(f"/api/presence/{quote(name)}/checkin"), f"presence {name}")


def call_announce(text: str) -> None:
    _send(_url("/api/announce"), f"announce {text}", data={"text": text})


def fetch_actions() -> dict[str, Any] | None:
    return _fetch("/api/actions", "actions")


def fetch_durations() -> dict[str, int]:
    return {name: int(entry["avg"]) for name, entry in _timings().items()}


def get_delay(name: str) -> timedelta | None:
    entry = _timings().get(name)
    return _parse_delay(entry["delay"]) if entry else None


def _url(path: str) -> str:
    return urljoin(config.settings.orc_base_url, path)


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


@functools.cache
def _timings() -> dict[str, dict[str, Any]]:
    actions = fetch_actions() or {}
    return {**actions.get("rooms", {}), **actions.get("routines", {}), **actions.get("plugins", {})}


def _parse_delay(value: str) -> timedelta:
    hours, minutes, seconds = value.split(":")
    return timedelta(hours=int(hours), minutes=int(minutes), seconds=float(seconds))
