from collections.abc import Sequence
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageMath

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


_INK_SPAN: int | None = None


def _ink(emoji: str, font: ImageFont.FreeTypeFont) -> tuple[Image.Image, tuple[int, int, int, int]]:
    raw = Image.new("RGBA", (EMOJI_NATIVE * 3, EMOJI_NATIVE * 3), (0, 0, 0, 0))
    ImageDraw.Draw(raw).text((EMOJI_NATIVE, EMOJI_NATIVE), emoji, font=font, embedded_color=True)
    box = raw.getchannel("A").getbbox()
    if box is None:
        raise ValueError(f"{EMOJI_FONT_PATH} renders nothing for {emoji!r}")
    return raw, box


def calibrate(emojis: Sequence[str]) -> None:
    # one scale for the whole set, so a thin glyph stays thin instead of being
    # stretched to the tile like a per-glyph fit would do
    global _INK_SPAN
    font = ImageFont.truetype(EMOJI_FONT_PATH, EMOJI_NATIVE)
    _INK_SPAN = max(max(b[2] - b[0], b[3] - b[1]) for _, b in (_ink(e, font) for e in emojis))


def render_emoji(emoji: str, target_size: int) -> Image.Image:
    if _INK_SPAN is None:
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


def save_countdown(seconds: int, out_path: Path, frame_ms: int = 1000) -> None:
    frames = [_text_frame(str(n)) for n in range(seconds, 0, -1)]
    frames.append(multiline_frame(WAITING_LINES, WAITING_FONT_SIZE))
    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=frame_ms,
        disposal=2,
        optimize=False,
    )
