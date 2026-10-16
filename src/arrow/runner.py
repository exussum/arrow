import argparse
import sys
import threading
from pathlib import Path

from arrow import api
from arrow.config import config

SEPARATOR = "-----"


def main() -> None:
    args = _parse_args(sys.argv[1:])
    if args.command == "icons":
        sys.exit(_icons(args.action, args.words))

    config.load(args.config, args.icons)
    if args.command == "check":
        sys.exit(_check())
    if args.command == "package":
        sys.exit(_package(Path(args.out) if args.out else config.icons))

    print("opening streamdeck", file=sys.stderr)
    manager = api.DeckManager.build_manager(brightness=config.settings.dim_brightness)
    manager.initialize()
    print("ready", file=sys.stderr)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        manager.shutdown()


def _icons(action: str, words: list[str]) -> int:
    print(SEPARATOR)
    if action == "search":
        for word in words:
            for char, name in api.search_icons(word):
                print(f"{char}\t--icon={name}")
            print(SEPARATOR)
    else:
        print(" ".join(f"--icon={api.icon_name(word)}" for word in words))
        print(SEPARATOR)
    return 0


def _check() -> int:
    problems = api.missing_files() + api.unknown_actions()
    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"{len(config.buttons) + len(config.routines) + len(config.others)} buttons, {len(problems)} problems")
    return 1 if problems else 0


def _package(out: Path) -> int:
    members = api.generate_icons() | api.generate_countdowns()
    api.write_zip(members, out)
    print(f"{out}: {len(members)} files, {out.stat().st_size // 1024} KiB")
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="arrow", description="Stream Deck client for orc")
    parser.add_argument("--config", help="config.arrow to load (default: $ARROW_CONFIG, else the packaged one)")
    parser.add_argument("--icons", help="icons.zip to read (default: beside the config)")
    commands = parser.add_subparsers(dest="command")

    commands.add_parser("check", help="check the config against the icons and orc")

    package = commands.add_parser("package", help="generate the icons into a zip")
    package.add_argument("out", nargs="?", help="where to write it (default: --icons)")

    icons = commands.add_parser("icons", help="look up emoji names")
    icons.add_argument("action", choices=("search", "name"))
    icons.add_argument("words", nargs="+")
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
