import io
import sys
import threading
import time
import unicodedata
import zipfile
from collections.abc import Callable, Sequence
from functools import partial
from pathlib import Path
from typing import IO

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageMath

from arrow.config import ICONS_DIR, config, countdown_targets, icon_targets
from arrow.dal import orc, streamdeck
from arrow.loader import Art, Icon
from arrow.models import Button, Dispatch, IconMode, Routine

SIZE = 144
BULB_BADGE = 84

FONTS_DIR = Path(__file__).resolve().parent / "fonts"

EMOJI_FONT_PATH = str(FONTS_DIR / "NotoColorEmoji.ttf")
EMOJI_NATIVE = 109
EMOJI_TARGET = 120
PAIR_TARGET = 84

TEXT_FONT_PATH = str(FONTS_DIR / "LiberationSans-Regular.ttf")
TEXT_FONT_SIZE = 110

WAITING_LINES = ("Waiting", "for routine", "to finish")
WAITING_FONT_SIZE = 22
DELAYED_LINES = ("Delayed", "will run", "after wait")
PROCESSING_TEXT = "processing..."
PROCESSING_FONT_SIZE = 18
LABEL_FONT_SIZE = 26
PRESENCE_DURATION = 1

RANGES = ((0x2190, 0x33FF), (0x1F000, 0x1FAFF))


_INK_SPAN: int | None = None


class DeckManager:
    def __init__(self, brightness: int, display: streamdeck.DisplayManager) -> None:
        self._brightness = brightness
        self._display = display
        self._dispatch = build_dispatch()
        self._dim_timer: threading.Timer | None = None
        self._dim_lock = threading.Lock()
        self._dim_active = False

    @classmethod
    def build_manager(cls, brightness: int) -> "DeckManager":
        deck = streamdeck.open_deck()
        try:
            gif_paths = [path for _, path in countdown_targets()]
            cache = streamdeck.ImageManager.build(deck, gif_paths)
        except Exception:
            deck.close()
            raise
        return cls(brightness=brightness, display=streamdeck.DisplayManager(deck=deck, cache=cache))

    def initialize(self) -> None:
        self._display.deck.reset()
        self._display.upload_icons(IconMode.ICONS)
        self.set_brightness(config.settings.dim_brightness)
        self._display.deck.set_key_callback(lambda d, k, p: self.on_key_change(k, p))

    def shutdown(self) -> None:
        self._cancel_dim()
        self._display.close()

    def set_brightness(self, level: int) -> None:
        self._display.set_brightness(level)
        self._brightness = level
        if level == config.settings.dim_brightness:
            self._display.on_dim()

    def on_key_change(self, key: int, pressed: bool) -> None:
        if not pressed:
            return
        elif self._brightness == config.settings.dim_brightness:
            self.set_brightness(config.settings.active_brightness)
            self._schedule_dim()
        elif key == config.key_of("help"):
            self._display.toggle_labels()
            self._schedule_dim()
        elif entry := self._dispatch.get(key):
            self._display.upload_icons(IconMode.BLANK)
            self._cancel_dim()
            self._run(key, entry.gif, entry.action, entry.name)
        else:
            print(f"button {key} unmapped", file=sys.stderr)

    def _run(self, key: int, gif_path: Path, action: Callable[[], object], name: str | None = None) -> None:
        self._notify_delay(key, name)
        done = threading.Event()
        animator = threading.Thread(
            target=self._display.play_countdown,
            args=(key, gif_path, done),
            daemon=True,
        )
        animator.start()
        try:
            action()
        finally:
            done.set()
            animator.join(timeout=5)
            self._display.upload_icons(IconMode.ICONS)
            self._schedule_dim()

    def _notify_delay(self, key: int, name: str | None) -> None:
        if name and orc.get_delay(name):
            self._display.show_delayed_notice(key)
            time.sleep(config.settings.delay_notice_seconds)

    def _schedule_dim(self) -> None:
        self._cancel_dim()
        with self._dim_lock:
            self._dim_active = True
        t = threading.Timer(config.settings.dim_delay_seconds, self._apply_dim)
        t.daemon = True
        t.start()
        self._dim_timer = t

    def _apply_dim(self) -> None:
        with self._dim_lock:
            if self._dim_active:
                self._dim_active = False
                self.set_brightness(config.settings.dim_brightness)

    def _cancel_dim(self) -> None:
        with self._dim_lock:
            self._dim_active = False
        if self._dim_timer:
            self._dim_timer.cancel()
            self._dim_timer = None


def package(argv: list[str]) -> int:
    source, out = (argv[0] if argv else None), Path(argv[1] if len(argv) > 1 else "icons.zip")
    config.load(source)
    members = build()
    write_zip(members, out)
    print(f"{out}: {len(members)} files, {out.stat().st_size // 1024} KiB")
    return 0


def build() -> dict[str, bytes]:
    return generate_icons() | generate_countdowns()


def generate_icons() -> dict[str, bytes]:
    calibrate([icon.char for art in config.art.values() for icon in (*art.icons, *filter(None, (art.badge,)))])
    out = {_name(path): _png(compose(config.art[art_key(key)])) for key, path in icon_targets(label=False)}
    out |= {_name(path): _png(multiline_frame(label_lines(key), LABEL_FONT_SIZE)) for key, path in icon_targets(label=True)}
    out["delayed.png"] = _png(multiline_frame(DELAYED_LINES, WAITING_FONT_SIZE))
    return out


def generate_countdowns() -> dict[str, bytes]:
    durations = orc.fetch_durations()
    named: dict[int, Button | Routine] = {**config.buttons, **config.routines}
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


def write_dir(members: dict[str, bytes], root: Path) -> None:
    for name, data in members.items():
        out = root / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)


def write_zip(members: dict[str, bytes], out: Path) -> None:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)


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


def glyph(icon: Icon, size: int) -> Image.Image:
    img = render_emoji(icon.char, size)
    if icon.filter == "dim":
        return desaturate(img)
    if icon.filter == "invert":
        return swap_white_to_black(img)
    return img


def art_key(key: int) -> str:
    if button := config.buttons.get(key):
        return f"{button.slug}/{button.action}"
    item = config.routines.get(key) or config.others[key]
    return item.slug


def label_lines(key: int) -> list[str]:
    if button := config.buttons.get(key):
        return wrap_words(button.display_name) + [button.action.capitalize()]
    item = config.routines.get(key) or config.others[key]
    return wrap_words(item.display_name)


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


def build_dispatch() -> dict[int, Dispatch]:
    presence = {
        key: Dispatch(ICONS_DIR / "countdowns" / "presence.gif", partial(orc.call_presence, config.settings.presence_name))
        for key, other in config.others.items()
        if other.slug == "presence"
    }
    rooms = {
        key: Dispatch(
            ICONS_DIR / "countdowns" / b.action / f"{b.slug}.gif",
            partial(orc.call_room, b.display_name, b.action),
            b.display_name,
        )
        for key, b in config.buttons.items()
    }
    routines = {
        key: Dispatch(
            ICONS_DIR / "countdowns" / "routines" / f"{r.slug}.gif",
            partial(orc.call_routine, r.orc_id or r.display_name, r.display_name),
            r.orc_id or r.display_name,
        )
        for key, r in config.routines.items()
    }
    return presence | rooms | routines


def icon_lookup(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "search":
        for char, name in search(" ".join(argv[1:])):
            print(f"{char}\t--icon={name}")
        return 0
    if len(argv) >= 2 and argv[0] == "name":
        print(" ".join(f"--icon={to_name(c)}" for c in argv[1:]))
        return 0
    print("usage: arrow icons search <word> | arrow icons name <emoji>...", file=sys.stderr)
    return 2


def search(query: str) -> list[tuple[str, str]]:
    return [(c, to_name(c)) for c, n in _named() if query.upper() in n]


def to_name(char: str) -> str:
    return unicodedata.name(char.replace("️", "")).lower().replace(" ", "-")


def to_char(name: str) -> str:
    return unicodedata.lookup(name.replace("-", " ").upper())


def calibrate(emojis: Sequence[str]) -> None:
    global _INK_SPAN
    font = ImageFont.truetype(EMOJI_FONT_PATH, EMOJI_NATIVE)
    _INK_SPAN = max(max(b[2] - b[0], b[3] - b[1]) for _, b in (_ink(e, font) for e in emojis))


def render_emoji(emoji: str, target_size: int) -> Image.Image:
    if not _INK_SPAN:
        raise RuntimeError("calibrate() must run before render_emoji()")
    raw, box = _ink(emoji, ImageFont.truetype(EMOJI_FONT_PATH, EMOJI_NATIVE))
    scale = target_size / _INK_SPAN
    ink = raw.crop(box).resize(
        (max(1, round((box[2] - box[0]) * scale)), max(1, round((box[3] - box[1]) * scale))),
        Image.Resampling.LANCZOS,
    )
    out = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
    out.alpha_composite(ink, ((target_size - ink.width) // 2, (target_size - ink.height) // 2))
    return out


def desaturate(img: Image.Image, brightness: float = 0.5) -> Image.Image:
    grey = ImageEnhance.Color(img).enhance(0.0)
    return ImageEnhance.Brightness(grey).enhance(brightness)


def swap_white_to_black(img: Image.Image, threshold: int = 200) -> Image.Image:
    r, g, b, a = img.split()
    mask = ImageMath.unsafe_eval(
        'convert(((r >= t) & (g >= t) & (b >= t) & (a > 0)) * 255, "L")',
        r=r,
        g=g,
        b=b,
        a=a,
        t=threshold,
    )
    black = Image.new("RGBA", img.size)
    black.putalpha(a)
    return Image.composite(black, img, mask)


def add_label_text(img: Image.Image, text: str, font_size: int = 20) -> None:
    font = ImageFont.truetype(TEXT_FONT_PATH, font_size)
    draw = ImageDraw.Draw(img)
    lines = text.split("\n")
    line_h = int(max(draw.textbbox((0, 0), line, font=font)[3] for line in lines)) + 4
    y = int(SIZE * 0.25)
    for line in lines:
        draw.text(
            (SIZE // 2, y),
            line,
            font=font,
            anchor="mt",
            fill=(0, 0, 0, 255),
            stroke_width=2,
            stroke_fill=(255, 255, 255, 255),
        )
        y += line_h


def multiline_frame(lines: Sequence[str], font_size: int, fg: str = "white", bg: str = "black") -> Image.Image:
    frame = Image.new("RGB", (SIZE, SIZE), bg)
    draw = ImageDraw.Draw(frame)
    font = ImageFont.truetype(TEXT_FONT_PATH, font_size)
    line_height = max(_text_height(draw, line, font) for line in lines) + 4
    y = (SIZE - (line_height * len(lines) - 4)) // 2
    for line in lines:
        _draw_h_centered(draw, line, font, y, fg)
        y += line_height
    return frame


def save_countdown(seconds: int, out: Path | IO[bytes], frame_ms: int = 1000) -> None:
    frames = [_text_frame(str(n)) for n in range(seconds, 0, -1)]
    frames.append(multiline_frame(WAITING_LINES, WAITING_FONT_SIZE))
    frames[0].save(
        out,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=frame_ms,
        disposal=2,
        optimize=False,
    )


def _ink(emoji: str, font: ImageFont.FreeTypeFont) -> tuple[Image.Image, tuple[int, int, int, int]]:
    raw = Image.new("RGBA", (EMOJI_NATIVE * 3, EMOJI_NATIVE * 3), (0, 0, 0, 0))
    ImageDraw.Draw(raw).text((EMOJI_NATIVE, EMOJI_NATIVE), emoji, font=font, embedded_color=True)
    box = raw.getchannel("A").getbbox()
    if not box:
        raise ValueError(f"{EMOJI_FONT_PATH} renders nothing for {emoji!r}")
    return raw, box


def _text_frame(text: str, fg: str = "white", bg: str = "black") -> Image.Image:
    text_font = ImageFont.truetype(TEXT_FONT_PATH, TEXT_FONT_SIZE)
    processing_font = ImageFont.truetype(TEXT_FONT_PATH, PROCESSING_FONT_SIZE)
    frame = Image.new("RGB", (SIZE, SIZE), bg)
    draw = ImageDraw.Draw(frame)
    big_top = (SIZE - _text_height(draw, text, text_font)) // 2 - 10
    proc_top = SIZE - _text_height(draw, PROCESSING_TEXT, processing_font) - 6
    _draw_h_centered(draw, text, text_font, big_top, fg)
    _draw_h_centered(draw, PROCESSING_TEXT, processing_font, proc_top, fg)
    return frame


def _text_height(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    b = draw.textbbox((0, 0), text, font=font)
    return int(b[3] - b[1])


def _draw_h_centered(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, top: int, fg: str) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(
        ((SIZE - (bbox[2] - bbox[0])) // 2 - bbox[0], top - bbox[1]),
        text,
        font=font,
        fill=fg,
    )


def _named() -> list[tuple[str, str]]:
    out = []
    for lo, hi in RANGES:
        for cp in range(lo, hi + 1):
            try:
                out.append((chr(cp), unicodedata.name(chr(cp))))
            except ValueError:
                pass
    return out


def _name(path: Path) -> str:
    return str(path.relative_to(ICONS_DIR))


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, "PNG")
    return buf.getvalue()
