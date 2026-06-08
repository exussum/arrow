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
    "living_room": "\U0001F6CB️",
    "office":      "\U0001F5A5️",
    "kitchen":     "\U0001F37D️",
}

ROUTINES = {
    "bed_time":             "\U0001F4A4",  # 💤
    "tv_lights":            "\U0001F4FA",  # 📺
    "early_morning_lights": "\U0001F56F",  # 🕯
    "all_lights_on":        "\U0001F4A1",  # 💡
    "dog":                  "\U0001F415",  # 🐕
    "silence":              "\U0001F507",  # 🔇
    "up_and_atom":          "⚛️", # ⚛️
    "back_on_schedule":     "\U0001F4C5",  # 📅
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
    partial.save(routines_out / "partial_tv_lights.png")

    reset = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    off_bulb = desaturate(render_emoji("\U0001F4A1", PAIR_TARGET))
    reset.alpha_composite(off_bulb, (0, 0))
    reset.alpha_composite(
        render_emoji("\U0001F507", PAIR_TARGET),  # 🔇
        (SIZE - PAIR_TARGET, SIZE - PAIR_TARGET),
    )
    reset.save(routines_out / "reset.png")

    dusk = swap_white_to_black(emoji_base("\U0001F306"))  # 🌆
    dusk.save(routines_out / "sunset_lights.png")


if __name__ == "__main__":
    main()
