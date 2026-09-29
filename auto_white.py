"""Select the newest black move and apply a validated white reply."""

import json
import os
import re
import sys
from pathlib import Path

from PIL import Image

from baduk_tools import LABELS, draw, read, save_move
from go_rules import group, play, transition


def boards():
    result = {}
    for path in Path('.').glob('go_board_*.png'):
        match = re.fullmatch(r'go_board_(\d+)\.png', path.name)
        if match:
            result[int(match.group(1))] = path
    return result


def move_board(before, point):
    return play(before, point, 'W')


def coord(label):
    match = re.fullmatch(r'([A-HJ-T])(1[0-9]|[1-9])', label.upper())
    if not match:
        raise ValueError('invalid coordinate')
    return LABELS.index(match.group(1)), 19 - int(match.group(2))


def output(**values):
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
        for k, v in values.items():
            f.write(f'{k}={v}\n')


def prepare():
    if Path('RESULT.md').exists():
        output(play='false')
        print('Game has ended.')
        return
    files = boards()
    if not files:
        raise ValueError('no board images')
    n = max(files)
    if n % 2 == 0:
        output(play='false')
        print(f'Latest board {n} is white; waiting for black.')
        return
    before, _, _, _ = read(files[n])
    previous = read(files[n-1])[0] if n > 1 else {}
    transition(previous, before, 'B', [read(files[k])[0] for k in sorted(files) if k < n])
    state = '\n'.join(f'{LABELS[x]}{19-y} {kind}' for (x, y), kind in
                      sorted(before.items(), key=lambda item: (item[0][1], item[0][0])))
    Path('board_state.txt').write_text(
        f'Input: {files[n].name}\nNext output: go_board_{n+1}.png\n'
        f'Black stones: {sum(v == "B" for v in before.values())}\n'
        f'White stones: {sum(v == "W" for v in before.values())}\n{state}\n',
        encoding='utf-8')
    output(play='true', source=files[n].name, target=f'go_board_{n+1}.png')
    print(Path('board_state.txt').read_text())


def restore_intersection(img, xs, ys, spacing, point):
    # A clean intersection copied from the earliest board avoids redrawing
    # the whole textured board when a capture removes one stone.
    base_path = Path(__file__).with_name('go_board_1.png')
    base = Image.open(base_path).convert('RGB')
    occupied, bx, by, _ = read(base_path)
    x, y = point
    stars = {3, 9, 15}
    def topology(p):
        px, py = p
        return (px if px in (0, 18) else -1,
                py if py in (0, 18) else -1,
                px in stars and py in stars)
    template = next((px, py) for py in range(19) for px in range(19)
                    if (px, py) not in occupied and topology((px, py)) == topology(point))
    radius = int(round(spacing * .53))
    sx, sy = round(bx[template[0]]), round(by[template[1]])
    dx, dy = round(xs[x]), round(ys[y])
    patch = base.crop((sx-radius, sy-radius, sx+radius+1, sy+radius+1))
    img.paste(patch, (dx-radius, dy-radius))


def apply():
    files = boards()
    n = max(files)
    if n % 2 != 1:
        raise ValueError('no pending black move')
    decision = json.loads(Path('move.json').read_text(encoding='utf-8'))
    if decision['decision'] == 'resign':
        Path('RESULT.md').write_text(
            f'백 패배 선언 — {files[n].name}\n\n{decision["reason"]}\n', encoding='utf-8')
        output(result='resign', target='RESULT.md')
        return
    if decision['decision'] != 'play':
        raise ValueError('invalid decision')
    point = coord(decision['move'])
    before, xs, ys, spacing = read(files[n])
    after, captured = move_board(before, point)
    if any(after == read(p)[0] for p in files.values()):
        raise ValueError('ko/repeated board position')
    target = Path(f'go_board_{n+1}.png')
    if target.exists():
        raise ValueError(f'{target} already exists')
    img = Image.open(files[n]).convert('RGB')
    for stone in captured:
        restore_intersection(img, xs, ys, spacing, stone)
    for stone, color in before.items():
        if stone not in captured and any(abs(stone[0]-q[0]) + abs(stone[1]-q[1]) == 1 for q in captured):
            draw(img, xs, ys, spacing, *stone, color)
    draw(img, xs, ys, spacing, *point, 'W')
    save_move(img, target, *point, 'W')
    actual = read(target)[0]
    if actual != after:
        target.unlink()
        raise ValueError('rendered board does not match the legal position')
    output(result='play', target=target.name)
    print(f'White {decision["move"]} -> {target}; captured {len(captured)} black stones')


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif sys.argv[1:] == ['apply']:
        apply()
    else:
        raise SystemExit('usage: auto_white.py prepare|apply')
