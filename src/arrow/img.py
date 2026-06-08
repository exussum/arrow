from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

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


def emoji_base(emoji: str) -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    rendered = render_emoji(emoji, EMOJI_TARGET)
    off = (SIZE - EMOJI_TARGET) // 2
    img.alpha_composite(rendered, (off, off))
    return img


def add_triangle(img: Image.Image, color) -> None:
    ImageDraw.Draw(img).polygon(
        [(SIZE, SIZE), (SIZE - TRI, SIZE), (SIZE, SIZE - TRI)],
        fill=color,
    )


def add_pushpin(img: Image.Image) -> None:
    pin = render_emoji(PUSHPIN, BADGE)
    img.alpha_composite(pin, (SIZE - BADGE, SIZE - BADGE))


def diagonal(top_left_emoji: str, bottom_right_emoji: str) -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    img.alpha_composite(render_emoji(top_left_emoji, PAIR_TARGET), (0, 0))
    img.alpha_composite(
        render_emoji(bottom_right_emoji, PAIR_TARGET),
        (SIZE - PAIR_TARGET, SIZE - PAIR_TARGET),
    )
    return img


def desaturate(img: Image.Image, brightness: float = 0.5) -> Image.Image:
    grey = ImageEnhance.Color(img).enhance(0.0)
    return ImageEnhance.Brightness(grey).enhance(brightness)


def swap_white_to_black(img: Image.Image, threshold: int = 200) -> Image.Image:
    out = img.copy()
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 0 and r >= threshold and g >= threshold and b >= threshold:
                px[x, y] = (0, 0, 0, a)
    return out


def _text_frame(text: str, fg: str = "white", bg: str = "black") -> Image.Image:
    frame = Image.new("RGB", (SIZE, SIZE), bg)
    draw = ImageDraw.Draw(frame)

    bbox = draw.textbbox((0, 0), text, font=_text_font)
    x = (SIZE - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (SIZE - (bbox[3] - bbox[1])) // 2 - bbox[1] - 10
    draw.text((x, y), text, font=_text_font, fill=fg)

    pbbox = draw.textbbox((0, 0), PROCESSING_TEXT, font=_processing_font)
    px = (SIZE - (pbbox[2] - pbbox[0])) // 2 - pbbox[0]
    py = SIZE - (pbbox[3] - pbbox[1]) - 6 - pbbox[1]
    draw.text((px, py), PROCESSING_TEXT, font=_processing_font, fill=fg)

    return frame


def _multiline_frame(lines, font_size: int, fg: str = "white", bg: str = "black") -> Image.Image:
    frame = Image.new("RGB", (SIZE, SIZE), bg)
    draw = ImageDraw.Draw(frame)
    font = ImageFont.truetype(TEXT_FONT_PATH, font_size)
    boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    line_height = max(b[3] - b[1] for b in boxes) + 4
    total = line_height * len(lines) - 4
    y = (SIZE - total) // 2
    for line, bbox in zip(lines, boxes):
        x = (SIZE - (bbox[2] - bbox[0])) // 2 - bbox[0]
        draw.text((x, y - bbox[1]), line, font=font, fill=fg)
        y += line_height
    return frame


def save_countdown(seconds: int, out_path: Path, frame_ms: int = 1000) -> None:
    frames = [_text_frame(str(n)) for n in range(seconds, 0, -1)]
    frames.append(_multiline_frame(WAITING_LINES, WAITING_FONT_SIZE))
    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=frame_ms,
        disposal=2,
        optimize=False,
    )
