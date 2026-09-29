"""Select the newest black move and apply a validated white reply."""

import json
import os
import re
import sys
from pathlib import Path

from PIL import Image

from baduk_tools import LABELS, draw, read


def boards():
    result = {}
    for path in Path('.').glob('go_board_*.png'):
        match = re.fullmatch(r'go_board_(\d+)\.png', path.name)
        if match:
            result[int(match.group(1))] = path
    return result


def group(board, point):
    color = board[point]
    seen, liberties, todo = set(), set(), [point]
    while todo:
        x, y = todo.pop()
        if (x, y) in seen:
            continue
        seen.add((x, y))
        for q in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if not (0 <= q[0] < 19 and 0 <= q[1] < 19):
                continue
            if q not in board:
                liberties.add(q)
            elif board[q] == color and q not in seen:
                todo.append(q)
    return seen, liberties


def move_board(before, point):
    if point in before:
        raise ValueError('occupied intersection')
    after = dict(before)
    after[point] = 'W'
    captured = set()
    x, y = point
    for q in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
        if after.get(q) == 'B':
            stones, liberties = group(after, q)
            if not liberties:
                captured |= stones
    for q in captured:
        del after[q]
    if not group(after, point)[1]:
        raise ValueError('suicide move')
    return after, captured


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
    if sum(v == 'B' for v in before.values()) != sum(v == 'W' for v in before.values()) + 1:
        raise ValueError('latest board is not a black-to-white position')
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
    base = Image.open('go_board_1.png').convert('RGB')
    bx, by = read('go_board_1.png')[1:3]
    x, y = point
    stars = {3, 9, 15}
    template = (3, 15) if x in stars and y in stars else (5, 5)
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
    if n >= 3 and files.get(n-2) and after == read(files[n-2])[0]:
        raise ValueError('immediate ko recapture')
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
    img.save(target)
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
