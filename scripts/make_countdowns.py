#!/usr/bin/env python3

import re
import sys
from pathlib import Path

from arrow import BUTTONS, ICONS_DIR, ROUTINES
from arrow.img import save_countdown

CONFIG_PATH = Path(__file__).resolve().parents[2] / "provision" / "roles" / "orc" / "files" / "config.md"
OUT_DIR = ICONS_DIR / "countdowns"


def parse_durations(text: str) -> dict[str, int]:
    match = re.search(r"#####\s+Durations\s*\n(.*?)(?:\n-{3,}|\Z)", text, re.DOTALL)
    if not match:
        raise RuntimeError("Durations section not found in config")
    durations: dict[str, int] = {}
    for line in match.group(1).splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 2:
            continue
        name, secs = cells
        if name in ("Name", "") or set(name) <= {"-", ":"}:
            continue
        durations[name] = int(secs)
    return durations


def main() -> int:
    durations = parse_durations(CONFIG_PATH.read_text())
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

    if missing:
        print("missing durations:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
