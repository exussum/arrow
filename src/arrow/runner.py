import sys
import threading

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from StreamDeck.DeviceManager import DeviceManager

from arrow import DIM_BRIGHTNESS
from arrow import api


def main():
    print("searching for streamdeck", file=sys.stderr)
    decks = DeviceManager().enumerate()
    if not decks:
        print("no streamdeck found", file=sys.stderr)
        return

    deck = decks[0]
    print(f"opening {deck.deck_type()}", file=sys.stderr)
    deck.open()
    deck.reset()

    api.upload_icons(deck)

    state = api.State(brightness=DIM_BRIGHTNESS)
    deck.set_brightness(DIM_BRIGHTNESS)

    print("starting scheduler", file=sys.stderr)
    scheduler = BackgroundScheduler(
        jobstores={"default": MemoryJobStore()},
        executors={"default": ThreadPoolExecutor(max_workers=1)},
    )
    scheduler.start()

    deck.set_key_callback(lambda d, k, p: api.on_key_change(d, state, scheduler, k, p))

    print("ready", file=sys.stderr)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.shutdown(wait=False)
        with deck:
            deck.close()


if __name__ == "__main__":
    main()
