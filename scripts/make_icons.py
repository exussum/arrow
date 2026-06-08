#!/usr/bin/env python3

from PIL import Image

from arrow import ICONS_DIR
from arrow.img import (
    OFF_COLOR,
    ON_COLOR,
    PAIR_TARGET,
    SIZE,
    add_pushpin,
    add_triangle,
    desaturate,
    diagonal,
    emoji_base,
    render_emoji,
    swap_white_to_black,
)

ROOMS = {
    "hall": "\U0001F6CB️",
    "study":      "\U0001F5A5️",
    "garden":     "\U0001F37D️",
}

ROUTINES = {
    "goodnight":             "\U0001F4A4",  # 💤
    "movie_night":            "\U0001F4FA",  # 📺
    "nightlights": "\U0001F56F",  # 🕯
    "everything":        "\U0001F4A1",  # 💡
    "cat":                  "\U0001F415",  # 🐕
    "hush":              "\U0001F507",  # 🔇
    "wake_up":          "⚛️", # ⚛️
    "weekly_review":     "\U0001F4C5",  # 📅
}

VARIANTS = {
    "on":     lambda img: add_triangle(img, ON_COLOR),
    "off":    lambda img: add_triangle(img, OFF_COLOR),
    "follow": add_pushpin,
}


def main():
    for variant, decorate in VARIANTS.items():
        out = ICONS_DIR / variant
        out.mkdir(parents=True, exist_ok=True)
        for name, emoji in ROOMS.items():
            img = emoji_base(emoji)
            decorate(img)
            img.save(out / f"{name}.png")

    routines_out = ICONS_DIR / "routines"
    routines_out.mkdir(parents=True, exist_ok=True)
    for name, emoji in ROUTINES.items():
        img = emoji_base(emoji)
        img.save(routines_out / f"{name}.png")

    partial = diagonal("\U0001F4FA", "\U0001F4A1")  # 📺 + 💡
    partial.save(routines_out / "dim_the_hall.png")

    reset = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    off_bulb = desaturate(render_emoji("\U0001F4A1", PAIR_TARGET))
    reset.alpha_composite(off_bulb, (0, 0))
    reset.alpha_composite(
        render_emoji("\U0001F507", PAIR_TARGET),  # 🔇
        (SIZE - PAIR_TARGET, SIZE - PAIR_TARGET),
    )
    reset.save(routines_out / "reset.png")

    dusk = swap_white_to_black(emoji_base("\U0001F306"))  # 🌆
    dusk.save(routines_out / "dusk.png")


if __name__ == "__main__":
    main()
