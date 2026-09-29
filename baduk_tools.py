"""Read a baduk board image and render a legal move with captures.

Detect the grid and stones, validate captures, suicide and board repetition,
and verify the rendered output. Both Black and White use the same rules.

    python baduk_tools.py read  <image>
    python baduk_tools.py play  <src> <dst> <gx> <gy> [B|W]  # 0-indexed
    python baduk_tools.py coords                        # board labels reference
    python baduk_tools.py turn                          # validated next turn

gx runs 0..18 left to right, gy runs 0..18 top to bottom.
"""
import sys
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from go_rules import play, transition

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
        kind = sys.argv[6].upper() if len(sys.argv) > 6 else "B"
        if kind not in ("B", "W") or not (0 <= gx < 19 and 0 <= gy < 19):
            raise SystemExit("expected 0..18 grid coordinates and stone B or W")
        source = Path(src)
        if Path(dst).resolve() == source.resolve() or Path(dst).exists():
            raise SystemExit('output must be a new file; never overwrite a board')
        pos, xs, ys, spacing = read(src)
        match = re.fullmatch(r'go_board_(\d+)\.png', source.name)
        history = []
        if match:
            n = int(match[1])
            if kind != ('B' if n % 2 == 0 else 'W'):
                raise SystemExit('wrong side to move for this board number')
            for p in source.parent.glob('go_board_*.png'):
                m = re.fullmatch(r'go_board_(\d+)\.png', p.name)
                if m and int(m[1]) <= n:
                    history.append(read(p)[0])
        after, captured = play(pos, (gx, gy), kind, history)
        img = Image.open(src).convert("RGB")
        if captured:
            from auto_white import restore_intersection
            for stone in captured:
                restore_intersection(img, xs, ys, spacing, stone)
            for stone, color in pos.items():
                if stone not in captured and any(abs(stone[0]-q[0])+abs(stone[1]-q[1]) == 1 for q in captured):
                    draw(img, xs, ys, spacing, *stone, color)
        draw(img, xs, ys, spacing, gx, gy, kind)
        img.save(dst)
        if read(dst)[0] != after:
            Path(dst).unlink()
            raise SystemExit('rendered board does not match legal position')
        print(f"{LABELS[gx]}{19 - gy} played -> {dst}; captured={len(captured)}")
    elif cmd == 'turn':
        if Path('RESULT.md').exists():
            print('turn=finished')
            return
        files = {int(m[1]): p for p in Path('.').glob('go_board_*.png')
                 if (m := re.fullmatch(r'go_board_(\d+)\.png', p.name))}
        n = max(files)
        after = read(files[n])[0]
        before = read(files[n-1])[0] if n > 1 else {}
        mover = 'B' if n % 2 else 'W'
        history = [read(files[k])[0] for k in sorted(files) if k < n]
        transition(before, after, mover, history)
        print(f'n={n}')
        print('turn=' + ('white' if mover == 'B' else 'black'))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
