import sys
import threading

from arrow import api, emoji
from arrow.config import config


def main() -> None:
    if sys.argv[1:2] == ["icons"]:
        sys.exit(emoji.main(sys.argv[2:]))

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
