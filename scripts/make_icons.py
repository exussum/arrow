#!/usr/bin/env python3

from PIL import Image

from arrow import BUTTONS, ICONS_DIR, OTHERS, ROUTINES
from arrow.img import (
    PAIR_TARGET,
    SIZE,
    add_bulb_off,
    add_bulb_on,
    add_label_text,
    add_pushpin,
    desaturate,
    diagonal,
    emoji_base,
    multiline_frame,
    render_emoji,
    swap_white_to_black,
)

LABEL_FONT_SIZE = 26


def wrap_words(text: str, max_chars: int = 10) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def label_image(lines: list[str], font_size: int = LABEL_FONT_SIZE):
    return multiline_frame(lines, font_size)


ROOMS = {
    "living_room": "\U0001f6cb️",
    "office": "\U0001f5a5️",
    "kitchen": "\U0001f37d️",
}

OTHER_ICONS = {
    "help": "❓",
    "presence": "\U0001f64b",  # 🙋
}

ROUTINE_ICONS = {
    "bed_time": "\U0001f4a4",  # 💤
    "tv_lights": "\U0001f4fa",  # 📺
    "early_morning_lights": "\U0001f56f",  # 🕯
    "all_lights_on": "\U0001f4a1",  # 💡
    "dog": "\U0001f415",  # 🐕
    "silence": "\U0001f507",  # 🔇
    "up_and_atom": "⚛️",  # ⚛️
    "back_on_schedule": "\U0001f4c5",  # 📅
}

VARIANTS = {
    "on": add_bulb_on,
    "off": add_bulb_off,
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
    for name, emoji in ROUTINE_ICONS.items():
        if name == "all_lights_on":
            continue
        img = emoji_base(emoji)
        img.save(routines_out / f"{name}.png")

    all_lights_emoji = "\U0001f4a1"
    img = emoji_base(all_lights_emoji)
    add_label_text(img, "All\nlights", font_size=40)
    img.save(routines_out / "all_lights_on.png")

    img = desaturate(emoji_base(all_lights_emoji))
    add_label_text(img, "All\nlights", font_size=40)
    img.save(routines_out / "all_lights_off.png")

    partial = diagonal("\U0001f4fa", "\U0001f4a1")  # 📺 + 💡
    partial.save(routines_out / "partial_tv_lights.png")

    reset = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    off_bulb = desaturate(render_emoji("\U0001f4a1", PAIR_TARGET))
    reset.alpha_composite(off_bulb, (0, 0))
    reset.alpha_composite(
        render_emoji("\U0001f507", PAIR_TARGET),  # 🔇
        (SIZE - PAIR_TARGET, SIZE - PAIR_TARGET),
    )
    reset.save(routines_out / "reset.png")

    dusk = swap_white_to_black(emoji_base("\U0001f306"))  # 🌆
    dusk.save(routines_out / "sunset_lights.png")

    labels_root = ICONS_DIR / "labels"
    seen_buttons: set[tuple[str, str]] = set()
    for button in BUTTONS.values():
        key = (button.slug, button.action)
        if key in seen_buttons:
            continue
        seen_buttons.add(key)
        label_dir = labels_root / button.action
        label_dir.mkdir(parents=True, exist_ok=True)
        lines = wrap_words(button.display_name) + [button.action.capitalize()]
        label_image(lines).save(label_dir / f"{button.slug}.png")

    routine_labels = labels_root / "routines"
    routine_labels.mkdir(parents=True, exist_ok=True)
    seen_routines: set[str] = set()
    for routine in ROUTINES.values():
        if routine.slug in seen_routines:
            continue
        seen_routines.add(routine.slug)
        label_image(wrap_words(routine.display_name)).save(routine_labels / f"{routine.slug}.png")

    for other in OTHERS.values():
        emoji_base(OTHER_ICONS[other.slug]).save(ICONS_DIR / f"{other.slug}.png")
        label_image(wrap_words(other.display_name)).save(labels_root / f"{other.slug}.png")


if __name__ == "__main__":
    main()
