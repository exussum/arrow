#!/usr/bin/env python3

import sys

from arrow import runner
from arrow.config import ICONS_DIR, config


def main() -> int:
    config.load()
    runner.write_dir(runner.countdowns(), ICONS_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
