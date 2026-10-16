#!/usr/bin/env python3

import sys

from arrow import api
from arrow.config import ICONS_DIR, config


def main() -> int:
    config.load()
    api.write_dir(api.generate_countdowns(), ICONS_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
