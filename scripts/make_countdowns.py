#!/usr/bin/env python3

import json
import sys
import urllib.request

from arrow import BUTTONS, HTTP_TIMEOUT, ICONS_DIR, ORC_BASE_URL, ROUTINES
from arrow.img import save_countdown

OUT_DIR = ICONS_DIR / "countdowns"
PRESENCE_DURATION = 1


def fetch_durations() -> dict[str, int]:
    with urllib.request.urlopen(f"{ORC_BASE_URL}/api/durations", timeout=HTTP_TIMEOUT) as r:
        return {name: int(secs) for name, secs in json.load(r).items()}


def main() -> int:
    durations = fetch_durations()
    missing: list[str] = []

    for button in BUTTONS.values():
        secs = durations.get(button.display_name)
        if secs is None:
            missing.append(f"button: {button.display_name}")
            continue
        out = OUT_DIR / button.action
        out.mkdir(parents=True, exist_ok=True)
        save_countdown(secs, out / f"{button.slug}.gif")

    routines_out = OUT_DIR / "routines"
    routines_out.mkdir(parents=True, exist_ok=True)
    for routine in ROUTINES.values():
        secs = durations.get(routine.display_name)
        if secs is None:
            missing.append(f"routine: {routine.display_name}")
            continue
        save_countdown(secs, routines_out / f"{routine.slug}.gif")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    save_countdown(PRESENCE_DURATION, OUT_DIR / "presence.gif")

    if missing:
        print("missing durations:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
