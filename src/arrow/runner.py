import io
import sys
import threading
import zipfile
from pathlib import Path

from PIL import Image

from arrow import api, arrow
from arrow.api import (
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
    save_countdown,
    swap_white_to_black,
)
from arrow.config import ICONS_DIR, config, countdown_targets, icon_targets
from arrow.dal import orc
from arrow.loader import Art, Icon

LABEL_FONT_SIZE = 26
PRESENCE_DURATION = 1

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


def _name(path: Path) -> str:
    return str(path.relative_to(ICONS_DIR))


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, "PNG")
    return buf.getvalue()


def icons() -> dict[str, bytes]:
    calibrate([icon.char for art in config.art.values() for icon in (*art.icons, *filter(None, (art.badge,)))])
    out = {_name(path): _png(compose(config.art[art_key(key)])) for key, path in icon_targets(label=False)}
    out |= {_name(path): _png(multiline_frame(label_lines(key), LABEL_FONT_SIZE)) for key, path in icon_targets(label=True)}
    out["delayed.png"] = _png(multiline_frame(DELAYED_LINES, WAITING_FONT_SIZE))
    return out


def countdowns() -> dict[str, bytes]:
    durations = orc.fetch_durations()
    named = {**config.buttons, **config.routines}
    out: dict[str, bytes] = {}
    for key, path in countdown_targets():
        if key not in named:
            seconds = PRESENCE_DURATION
        else:
            display = named[key].display_name
            if display not in durations:
                print(f"no duration for {display!r} — countdown will be a single frame", file=sys.stderr)
            seconds = durations.get(display, 0)
        buf = io.BytesIO()
        save_countdown(seconds, buf)
        out[_name(path)] = buf.getvalue()
    return out


def build() -> dict[str, bytes]:
    return icons() | countdowns()


def write_dir(members: dict[str, bytes], root: Path) -> None:
    for name, data in members.items():
        out = root / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)


def write_zip(members: dict[str, bytes], out: Path) -> None:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)


def package(argv: list[str]) -> int:
    source, out = (argv[0] if argv else None), Path(argv[1] if len(argv) > 1 else "icons.zip")
    config.load(source)
    members = build()
    write_zip(members, out)
    print(f"{out}: {len(members)} files, {out.stat().st_size // 1024} KiB")
    return 0


def main() -> None:
    if sys.argv[1:2] == ["icons"]:
        sys.exit(api.icon_lookup(sys.argv[2:]))
    if sys.argv[1:2] == ["check"]:
        sys.exit(arrow.main(sys.argv[2:]))
    if sys.argv[1:2] == ["package"]:
        sys.exit(package(sys.argv[2:]))

    config.load()

    print("opening streamdeck", file=sys.stderr)
    manager = api.DeckManager.build_manager(brightness=config.settings.dim_brightness)
    manager.initialize()
    print("ready", file=sys.stderr)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        manager.shutdown()


if __name__ == "__main__":
    main()
