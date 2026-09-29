"""Append the last move's number and coordinate below the board image.

    python annotate_move.py <image> <move-number> <B|W> <coord>

The strip goes outside the grid, so `baduk_tools.read` is unaffected.
"""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

STRIP = 64


def font(size):
    for name in ("malgun.ttf", "arial.ttf", "DejaVuSans.ttf"):
        for base in (r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu"):
            path = os.path.join(base, name)
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def board_height(img):
    stored = img.info.get('baduk_board_height')
    if stored is not None:
        height = int(stored)
        if not 0 < height <= img.height:
            raise ValueError('invalid board height metadata')
        return height
    # Older annotated boards have no metadata. Match the original board size.
    original = Path(__file__).with_name('go_board_1.png')
    if original.exists():
        with Image.open(original) as base:
            if img.width == base.width and img.height >= base.height:
                return base.height
    return img.height


def save_annotated(img, path, number, color, coord):
    if color not in ('B', 'W'):
        raise ValueError('invalid move color')
    w, h = img.width, board_height(img)
    img = img.crop((0, 0, w, h)).convert('RGB')
    bg = img.getpixel((8, h // 2))
    out = Image.new("RGB", (w, h + STRIP), bg)
    out.paste(img, (0, 0))
    draw = ImageDraw.Draw(out)
    label = f"{number}  {'Black' if color == 'B' else 'White'} {coord}"
    draw.text((w // 2, h + STRIP // 2), label, fill=(60, 40, 20),
              anchor="mm", font=font(int(STRIP * 0.55)))
    metadata = PngInfo()
    metadata.add_text('baduk_board_height', str(h))
    metadata.add_text('baduk_last_move', f'{number} {color} {coord}')
    out.save(path, pnginfo=metadata)
    return label


def annotate(path, number, color, coord):
    with Image.open(path) as img:
        return save_annotated(img, path, number, color, coord)


if __name__ == "__main__":
    path, number, color, coord = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    print(annotate(path, number, color, coord), "->", path)
