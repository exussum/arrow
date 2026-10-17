from pathlib import Path

from arrow.config import config

config.load(Path(__file__).parent / "fixture" / "base.arrow")
