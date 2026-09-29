"""Shared 19x19 rules. Board dictionaries map (x, y) to B or W."""
SIZE = 19

def neighbors(point):
    x, y = point
    return tuple(q for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))
                 if 0 <= q[0] < SIZE and 0 <= q[1] < SIZE)

def group(board, point):
    color = board[point]
    stones, liberties, todo = set(), set(), [point]
    while todo:
        p = todo.pop()
        if p in stones:
            continue
        stones.add(p)
        for q in neighbors(p):
            if q not in board:
                liberties.add(q)
            elif board[q] == color and q not in stones:
                todo.append(q)
    return stones, liberties

def play(board, point, color, history=()):
    if color not in ('B', 'W'):
        raise ValueError('invalid stone color')
    if not (0 <= point[0] < SIZE and 0 <= point[1] < SIZE):
        raise ValueError('intersection out of bounds')
    if point in board:
        raise ValueError('occupied intersection')
    after = dict(board)
    after[point] = color
    opponent = 'W' if color == 'B' else 'B'
    captured = set()
    for q in neighbors(point):
        if after.get(q) == opponent:
            stones, liberties = group(after, q)
            if not liberties:
                captured.update(stones)
    for q in captured:
        del after[q]
    if not group(after, point)[1]:
        raise ValueError('suicide move')
    if any(after == previous for previous in history):
        raise ValueError('ko/repeated board position')
    return after, captured

def transition(before, after, color, history=()):
    added = set(after) - set(before)
    if len(added) != 1:
        raise ValueError('expected exactly one new stone')
    point = next(iter(added))
    if after[point] != color:
        raise ValueError('unexpected mover color')
    expected, captured = play(before, point, color, history)
    if after != expected:
        raise ValueError('image transition does not match a legal move and captures')
    return point, captured
