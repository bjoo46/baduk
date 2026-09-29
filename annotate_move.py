"""Append the last move's number and coordinate below the board image.

    python annotate_move.py <image> <move-number> <B|W> <coord>

The strip goes outside the grid, so `baduk_tools.read` is unaffected.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

STRIP = 64


def font(size):
    for name in ("malgun.ttf", "arial.ttf", "DejaVuSans.ttf"):
        for base in (r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu"):
            path = os.path.join(base, name)
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def annotate(path, number, color, coord):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    bg = img.getpixel((8, h // 2))
    out = Image.new("RGB", (w, h + STRIP), bg)
    out.paste(img, (0, 0))
    draw = ImageDraw.Draw(out)
    label = f"{number}  {'Black' if color == 'B' else 'White'} {coord}"
    draw.text((w // 2, h + STRIP // 2), label, fill=(60, 40, 20),
              anchor="mm", font=font(int(STRIP * 0.55)))
    out.save(path)
    return label


if __name__ == "__main__":
    path, number, color, coord = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    print(annotate(path, number, color, coord), "->", path)
