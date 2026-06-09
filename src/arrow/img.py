from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageMath

SIZE = 144
TRI = 42
BADGE = 56
ON_COLOR = (0, 200, 0, 255)
OFF_COLOR = (220, 0, 0, 255)
PUSHPIN = "\U0001F4CC"

EMOJI_FONT_PATH = "/System/Library/Fonts/Apple Color Emoji.ttc"
EMOJI_NATIVE = 160
EMOJI_TARGET = 120
PAIR_TARGET = 84

TEXT_FONT_PATH = "/System/Library/Fonts/HelveticaNeue.ttc"
TEXT_FONT_SIZE = 110

WAITING_LINES = ("Waiting", "for routine", "to finish")
WAITING_FONT_SIZE = 22
PROCESSING_TEXT = "processing..."
PROCESSING_FONT_SIZE = 18

_emoji_font = ImageFont.truetype(EMOJI_FONT_PATH, EMOJI_NATIVE)
_text_font = ImageFont.truetype(TEXT_FONT_PATH, TEXT_FONT_SIZE)
_processing_font = ImageFont.truetype(TEXT_FONT_PATH, PROCESSING_FONT_SIZE)


def render_emoji(emoji: str, target_size: int) -> Image.Image:
    raw = Image.new("RGBA", (EMOJI_NATIVE, EMOJI_NATIVE), (0, 0, 0, 0))
    ImageDraw.Draw(raw).text((0, 0), emoji, font=_emoji_font, embedded_color=True)
    return raw.resize((target_size, target_size), Image.LANCZOS)


def _paste_emoji(img: Image.Image, emoji: str, target: int, pos: tuple[int, int]) -> None:
    img.alpha_composite(render_emoji(emoji, target), pos)


def emoji_base(emoji: str) -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    off = (SIZE - EMOJI_TARGET) // 2
    _paste_emoji(img, emoji, EMOJI_TARGET, (off, off))
    return img


def add_triangle(img: Image.Image, color) -> None:
    ImageDraw.Draw(img).polygon(
        [(SIZE, SIZE), (SIZE - TRI, SIZE), (SIZE, SIZE - TRI)],
        fill=color,
    )


def add_pushpin(img: Image.Image) -> None:
    _paste_emoji(img, PUSHPIN, BADGE, (SIZE - BADGE, SIZE - BADGE))


def diagonal(top_left_emoji: str, bottom_right_emoji: str) -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    _paste_emoji(img, top_left_emoji, PAIR_TARGET, (0, 0))
    _paste_emoji(img, bottom_right_emoji, PAIR_TARGET, (SIZE - PAIR_TARGET, SIZE - PAIR_TARGET))
    return img


def desaturate(img: Image.Image, brightness: float = 0.5) -> Image.Image:
    grey = ImageEnhance.Color(img).enhance(0.0)
    return ImageEnhance.Brightness(grey).enhance(brightness)


def swap_white_to_black(img: Image.Image, threshold: int = 200) -> Image.Image:
    r, g, b, a = img.split()
    mask = ImageMath.unsafe_eval(
        'convert(((r >= t) & (g >= t) & (b >= t) & (a > 0)) * 255, "L")',
        r=r, g=g, b=b, a=a, t=threshold,
    )
    black = Image.new("RGBA", img.size)
    black.putalpha(a)
    return Image.composite(black, img, mask)


def _text_height(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    b = draw.textbbox((0, 0), text, font=font)
    return b[3] - b[1]


def _draw_h_centered(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, top: int, fg: str
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(
        ((SIZE - (bbox[2] - bbox[0])) // 2 - bbox[0], top - bbox[1]),
        text,
        font=font,
        fill=fg,
    )


def _text_frame(text: str, fg: str = "white", bg: str = "black") -> Image.Image:
    frame = Image.new("RGB", (SIZE, SIZE), bg)
    draw = ImageDraw.Draw(frame)
    big_top = (SIZE - _text_height(draw, text, _text_font)) // 2 - 10
    proc_top = SIZE - _text_height(draw, PROCESSING_TEXT, _processing_font) - 6
    _draw_h_centered(draw, text, _text_font, big_top, fg)
    _draw_h_centered(draw, PROCESSING_TEXT, _processing_font, proc_top, fg)
    return frame


def multiline_frame(lines, font_size: int, fg: str = "white", bg: str = "black") -> Image.Image:
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
