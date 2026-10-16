import sys

from arrow.config import ICONS_DIR, config, countdown_targets, icon_targets
from arrow.dal import orc


def missing_files() -> list[str]:
    paths = [path for _, path in icon_targets(label=False) + icon_targets(label=True) + countdown_targets()]
    paths.append(ICONS_DIR / "delayed.png")
    return [f"missing {path.relative_to(ICONS_DIR)} — run make_icons" for path in dict.fromkeys(paths) if not path.exists()]


def against_orc() -> list[str]:
    actions = orc.fetch_actions()
    if not actions:
        print(f"skipped orc checks: {config.settings.orc_base_url}/api/actions did not answer", file=sys.stderr)
        return []

    problems = []
    for room in dict.fromkeys(button.display_name for button in config.buttons.values()):
        if room not in actions["rooms"]:
            problems.append(f"room {room!r} is not a room in orc")
    for routine in config.routines.values():
        if routine.orc_id not in actions["routines"] and routine.orc_id not in actions["plugins"]:
            problems.append(f"{routine.slug}: orc has no action {routine.orc_id!r}")
    if config.settings.presence_name not in actions["people"]:
        problems.append(f"presence_name {config.settings.presence_name!r} is not a person in orc")
    return problems


def check(argv: list[str]) -> int:
    config.load(argv[0] if argv else None)
    problems = missing_files() + against_orc()
    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"{len(config.buttons) + len(config.routines) + len(config.others)} buttons, {len(problems)} problems")
    return 1 if problems else 0
