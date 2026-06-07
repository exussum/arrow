from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

SIZE = 144
TRI = 42
BADGE = 56  # pushpin overlay size
YELLOW = (255, 204, 0, 255)
DARK_GREY = (60, 60, 60, 255)
FONT_PATH = "/System/Library/Fonts/Apple Color Emoji.ttc"
NATIVE = 160  # Apple Color Emoji's only valid strike size in PIL
EMOJI_TARGET = 120
PAIR_TARGET = 84  # per-emoji size when two are placed side by side

ROOMS = {
    "hall": "\U0001F6CB️",
    "study":      "\U0001F5A5️",
    "garden":     "\U0001F37D️",
    "bedroom":     "\U0001F6CF️",
}
PUSHPIN = "\U0001F4CC"

ROUTINES = {
    "goodnight":             "\U0001F4A4",  # 💤
    "movie_night":            "\U0001F4FA",  # 📺
    "nightlights": "\U0001FA94",  # 🪔
    "everything":        "\U0001F4A1",  # 💡
    "cat":                  "\U0001F415",  # 🐕
    "hush":              "\U0001F507",  # 🔇
}

OUT_DIR = Path(__file__).resolve().parents[1] / "src" / "arrow" / "icons"

font = ImageFont.truetype(FONT_PATH, NATIVE)


def render_emoji(emoji: str, target_size: int) -> Image.Image:
    raw = Image.new("RGBA", (NATIVE, NATIVE), (0, 0, 0, 0))
    ImageDraw.Draw(raw).text((0, 0), emoji, font=font, embedded_color=True)
    return raw.resize((target_size, target_size), Image.LANCZOS)


def base(emoji: str) -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    rendered = render_emoji(emoji, EMOJI_TARGET)
    off = (SIZE - EMOJI_TARGET) // 2
    img.alpha_composite(rendered, (off, off))
    return img


def add_triangle(img: Image.Image, color):
    ImageDraw.Draw(img).polygon(
        [(SIZE, SIZE), (SIZE - TRI, SIZE), (SIZE, SIZE - TRI)],
        fill=color,
    )


def add_pushpin(img: Image.Image):
    pin = render_emoji(PUSHPIN, BADGE)
    img.alpha_composite(pin, (SIZE - BADGE, SIZE - BADGE))


VARIANTS = {
    "on":     lambda img: add_triangle(img, YELLOW),
    "off":    lambda img: add_triangle(img, DARK_GREY),
    "follow": add_pushpin,
}


def pair(left_emoji: str, right_emoji: str) -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    y = (SIZE - PAIR_TARGET) // 2
    gap = (SIZE - 2 * PAIR_TARGET) // 3
    img.alpha_composite(render_emoji(left_emoji, PAIR_TARGET), (gap, y))
    img.alpha_composite(render_emoji(right_emoji, PAIR_TARGET), (gap * 2 + PAIR_TARGET, y))
    return img


def desaturate(img: Image.Image, brightness: float = 0.5) -> Image.Image:
    grey = ImageEnhance.Color(img).enhance(0.0)
    return ImageEnhance.Brightness(grey).enhance(brightness)


def main():
    for variant, decorate in VARIANTS.items():
        out = OUT_DIR / variant
        out.mkdir(parents=True, exist_ok=True)
        for name, emoji in ROOMS.items():
            img = base(emoji)
            decorate(img)
            img.save(out / f"{name}.png")
            print(f"wrote {variant}/{name}.png")

    routines_out = OUT_DIR / "routines"
    routines_out.mkdir(parents=True, exist_ok=True)
    for name, emoji in ROUTINES.items():
        img = base(emoji)
        img.save(routines_out / f"{name}.png")
        print(f"wrote routines/{name}.png")

    partial = pair("\U0001F4FA", "\U0001F4A1")  # 📺 + 💡
    partial.save(routines_out / "dim_the_hall.png")
    print("wrote routines/dim_the_hall.png")

    off_bulb = desaturate(base("\U0001F4A1"))
    off_bulb.save(routines_out / "everything_off.png")
    print("wrote routines/everything_off.png")


if __name__ == "__main__":
    main()
