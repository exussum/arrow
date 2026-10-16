import sys
import threading

from arrow import api, arrow
from arrow.config import config

COMMANDS = {"icons": api.icon_lookup, "check": arrow.check, "package": api.package}


def main() -> None:
    if command := COMMANDS.get(sys.argv[1] if sys.argv[1:] else ""):
        sys.exit(command(sys.argv[2:]))

    config.load()

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


if __name__ == "__main__":
    main()
