#!/usr/bin/env python3

from arrow import api
from arrow.config import ICONS_DIR, config


def main() -> int:
    config.load()
    api.write_dir(api.generate_icons(), ICONS_DIR)
    return 0


if __name__ == "__main__":
    main()
