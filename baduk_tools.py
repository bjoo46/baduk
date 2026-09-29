"""Read a baduk board image and draw a stone onto it.

Used by the 1-minute black-move loop: load the highest-numbered board image,
detect the grid and existing stones, then draw the black move on top.

    python baduk_tools.py read  <image>
    python baduk_tools.py play  <src> <dst> <gx> <gy>     # gx, gy are 0-indexed
    python baduk_tools.py coords                        # board labels reference

gx runs 0..18 left to right, gy runs 0..18 top to bottom.
"""
import sys

import numpy as np
from PIL import Image, ImageDraw

LABELS = "ABCDEFGHJKLMNOPQRST"


def luma(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def _line_centers(idx):
    groups, cur = [], [int(idx[0])]
    for v in idx[1:]:
        if v - cur[-1] <= 3:
            cur.append(int(v))
        else:
            groups.append(cur)
            cur = [int(v)]
    groups.append(cur)
    return [sum(g) / len(g) for g in groups]


def find_grid(a):
    dark = luma(a) < 80
    h, w = dark.shape
    rows = np.where(dark.sum(axis=1) > 0.5 * w)[0]
    cols = np.where(dark.sum(axis=0) > 0.5 * h)[0]
    if len(rows) == 0 or len(cols) == 0:
        raise ValueError("no grid lines found")
    return _line_centers(cols), _line_centers(rows)


def read(path):
    """Return {(gx, gy): 'B'|'W'} for occupied points, plus grid and spacing."""
    img = Image.open(path).convert("RGB")
    a = np.asarray(img, dtype=np.float32)
    xs, ys = find_grid(a)
    if len(xs) != 19 or len(ys) != 19:
        raise ValueError(f"expected 19x19 grid, found {len(xs)}x{len(ys)}")
    spacing = ((xs[-1] - xs[0]) + (ys[-1] - ys[0])) / 36.0
    # Sample a ring well inside a stone body, so the rim and the specular
    # highlight (both offset from the centre) cannot decide the reading.
    r = 0.30 * spacing
    ring = [(int(round(r * np.cos(t))), int(round(r * np.sin(t))))
            for t in np.linspace(0, 2 * np.pi, 16, endpoint=False)]
    pos = {}
    for gy in range(19):
        for gx in range(19):
            cx, cy = int(round(xs[gx])), int(round(ys[gy]))
            samples = []
            for ox, oy in ring:
                x, y = cx + ox, cy + oy
                if x < 1 or y < 1 or x >= a.shape[1] - 1 or y >= a.shape[0] - 1:
                    continue
                samples.append(a[y - 1:y + 2, x - 1:x + 2].reshape(-1, 3))
            if not samples:
                continue
            px = np.concatenate(samples)
            lum = float(np.median(luma(px)))
            rb = float(np.median(px[:, 0] - px[:, 2]))
            if lum < 120:
                pos[(gx, gy)] = "B"
            elif lum > 190 and rb < 60:
                pos[(gx, gy)] = "W"
    return pos, xs, ys, spacing


def draw(img, xs, ys, spacing, gx, gy, kind):
    d = ImageDraw.Draw(img)
    cx, cy = xs[gx], ys[gy]
    rad = int(round(spacing * 0.47))
    shadow = max(1, int(round(spacing * 0.08)))
    d.ellipse([cx - rad + shadow, cy - rad + shadow * 2,
               cx + rad + shadow, cy + rad + shadow * 2], fill=(146, 114, 72))
    if kind == "W":
        d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(168, 166, 158))
        rad -= max(1, int(round(spacing * 0.05)))
    base = (20, 20, 24) if kind == "B" else (232, 230, 222)
    d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=base)
    for i in range(48):
        t = (i + 1) / 48.0
        rr = rad * (1 - t * 0.80)
        off = -rad * 0.32 * t
        col = tuple(int(b + (255 - b) * t * t * 0.60) for b in base)
        d.ellipse([cx + off - rr, cy + off - rr, cx + off + rr, cy + off + rr], fill=col)
    return img


def main():
    cmd = sys.argv[1]
    if cmd == "read":
        pos, xs, ys, spacing = read(sys.argv[2])
        for (gx, gy), k in sorted(pos.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            print(f"{LABELS[gx]}{19 - gy} {k}")
        print(f"-- stones={len(pos)} black={sum(1 for v in pos.values() if v == 'B')} "
              f"white={sum(1 for v in pos.values() if v == 'W')} spacing={spacing:.1f}")
    elif cmd == "play":
        src, dst, gx, gy = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
        pos, xs, ys, spacing = read(src)
        if (gx, gy) in pos:
            raise SystemExit(f"({gx},{gy}) {LABELS[gx]}{19 - gy} is already occupied")
        img = Image.open(src).convert("RGB")
        draw(img, xs, ys, spacing, gx, gy, "B")
        img.save(dst)
        print(f"{LABELS[gx]}{19 - gy} played -> {dst}")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
