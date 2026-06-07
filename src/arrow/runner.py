import sys
import threading

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from arrow import DIM_BRIGHTNESS
from arrow import api


def main():
    state = api.State(brightness=DIM_BRIGHTNESS)

    deck = api.get_deck()
    print("opening streamdeck", file=sys.stderr)

    api.initialize_deck(deck)

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
        api.shutdown_deck(deck)


if __name__ == "__main__":
    main()
