#!/usr/bin/env python3

from PIL import Image

from arrow.config import ICONS_DIR, config
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


def targets() -> dict[str, tuple[str, str, list[str]]]:
    # art key -> (icon path, label path, label lines), paths relative to ICONS_DIR
    out: dict[str, tuple[str, str, list[str]]] = {}
    for b in config.buttons.values():
        key = f"{b.slug}/{b.action}"
        lines = wrap_words(b.display_name) + [b.action.capitalize()]
        out[key] = (f"{b.action}/{b.slug}.png", f"labels/{b.action}/{b.slug}.png", lines)
    for r in config.routines.values():
        out[r.slug] = (f"routines/{r.slug}.png", f"labels/routines/{r.slug}.png", wrap_words(r.display_name))
    for o in config.others.values():
        out[o.slug] = (f"{o.slug}.png", f"labels/{o.slug}.png", wrap_words(o.display_name))
    return out


def main():
    config.load()
    calibrate([icon.char for art in config.art.values() for icon in (*art.icons, *filter(None, (art.badge,)))])

    for key, (icon_path, label_path, lines) in targets().items():
        for path, image in ((icon_path, compose(config.art[key])), (label_path, label_image(lines))):
            out = ICONS_DIR / path
            out.parent.mkdir(parents=True, exist_ok=True)
            image.save(out)

    multiline_frame(DELAYED_LINES, WAITING_FONT_SIZE).save(ICONS_DIR / "delayed.png")


if __name__ == "__main__":
    main()
