#!/usr/bin/env python3

from arrow import runner
from arrow.config import ICONS_DIR, config


def main() -> int:
    config.load()
    runner.write_dir(runner.icons(), ICONS_DIR)
    return 0


if __name__ == "__main__":
    main()
