#!/usr/bin/env python3

from pathlib import Path

from PIL import Image

from arrow.config import ICONS_DIR, config, icon_targets
from arrow.img import (
    BULB_BADGE,
    DELAYED_LINES,
    EMOJI_TARGET,
    PAIR_TARGET,
    SIZE,
    WAITING_FONT_SIZE,
    add_label_text,
    calibrate,
    desaturate,
    multiline_frame,
    render_emoji,
    swap_white_to_black,
)
from arrow.loader import Art, Icon

LABEL_FONT_SIZE = 26

FILTERS = {"dim": desaturate, "invert": swap_white_to_black}


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


def glyph(icon: Icon, size: int) -> Image.Image:
    img = render_emoji(icon.char, size)
    return FILTERS[icon.filter](img) if icon.filter else img


def compose(art: Art) -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    if len(art.icons) == 2:
        img.alpha_composite(glyph(art.icons[0], PAIR_TARGET), (0, 0))
        img.alpha_composite(glyph(art.icons[1], PAIR_TARGET), (SIZE - PAIR_TARGET, SIZE - PAIR_TARGET))
    else:
        off = (SIZE - EMOJI_TARGET) // 2
        img.alpha_composite(glyph(art.icons[0], EMOJI_TARGET), (off, off))
        if art.badge:
            img.alpha_composite(glyph(art.badge, BULB_BADGE), (SIZE - BULB_BADGE, SIZE - BULB_BADGE))
    if art.text:
        add_label_text(img, "\n".join(wrap_words(art.text, max_chars=6)), font_size=40)
    return img


def art_key(key: int) -> str:
    if (button := config.buttons.get(key)) is not None:
        return f"{button.slug}/{button.action}"
    item = config.routines.get(key) or config.others[key]
    return item.slug


def label_lines(key: int) -> list[str]:
    if (button := config.buttons.get(key)) is not None:
        return wrap_words(button.display_name) + [button.action.capitalize()]
    item = config.routines.get(key) or config.others[key]
    return wrap_words(item.display_name)


def save(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def main():
    config.load()
    calibrate([icon.char for art in config.art.values() for icon in (*art.icons, *filter(None, (art.badge,)))])

    for key, path in icon_targets(label=False):
        save(compose(config.art[art_key(key)]), path)
    for key, path in icon_targets(label=True):
        save(label_image(label_lines(key)), path)

    multiline_frame(DELAYED_LINES, WAITING_FONT_SIZE).save(ICONS_DIR / "delayed.png")


if __name__ == "__main__":
    main()
