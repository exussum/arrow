import sys
import threading

from arrow import DIM_BRIGHTNESS, api


def main() -> None:
    print("opening streamdeck", file=sys.stderr)
    manager = api.DeckManager.build_manager(brightness=DIM_BRIGHTNESS)
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
