"""Tests for Pacific Atlantic Water Flow. The answer is a list of [r, c] cells in any order
("compare": "unordered" in problem.json).

The time-limited tests defeat the search-from-every-cell approach (naive() below): in a large
basin every inner cell searches the whole basin and reaches neither ocean, and on a slope rising
towards the Atlantic every cell searches the whole rectangle above and to the left of it without
reaching the Atlantic. Both are O((m * n)^2) for that approach, against two O(m * n) floods from
the oceans."""

import random

STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def basin(n, rim=9, floor=1):
    """An n x n bowl: a rim of height `rim` around a flat floor."""
    return [
        [rim if r in (0, n - 1) or c in (0, n - 1) else floor for c in range(n)] for r in range(n)
    ]


def slope(rows, cols, towards_atlantic=True):
    """Heights rising by one per step towards the bottom-right (or towards the top-left)."""
    if towards_atlantic:
        return [[r + c for c in range(cols)] for r in range(rows)]
    return [[rows + cols - r - c for c in range(cols)] for r in range(rows)]


def pyramid(n):
    """Highest in the middle, falling by one per step towards every edge."""
    return [[min(r, c, n - 1 - r, n - 1 - c) for c in range(n)] for r in range(n)]


def terrain(seed, rows, cols, high):
    rng = random.Random(seed)
    return [[rng.randint(0, high) for _ in range(cols)] for _ in range(rows)]


SHOWN = [
    {
        "name": "Example 1",
        "args": ([[1, 2, 3, 4], [2, 6, 7, 3], [3, 5, 4, 2], [4, 3, 2, 1]],),
        "expect": [[0, 3], [1, 1], [1, 2], [2, 1], [3, 0]],
    },
    {
        "name": "Example 2",
        "args": ([[1, 1, 1], [1, 0, 1], [1, 1, 1]],),
        "expect": [[0, 0], [0, 1], [0, 2], [1, 0], [1, 2], [2, 0], [2, 1], [2, 2]],
    },
    {
        "name": "Example 3",
        "args": ([[1, 1, 3], [1, 2, 3], [3, 3, 3]],),
        "expect": [[0, 2], [1, 2], [2, 0], [2, 1], [2, 2]],
    },
]

HIDDEN = [
    {"name": "one cell", "args": ([[7]],), "expect": [[0, 0]]},
    {
        "name": "one row",
        "args": ([[1, 2, 3, 2, 1]],),
        "expect": [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4]],
    },
    {
        "name": "one column",
        "args": ([[3], [1], [4], [1], [5]],),
        "expect": [[0, 0], [1, 0], [2, 0], [3, 0], [4, 0]],
    },
    {"name": "2 x 2, low corners", "args": ([[1, 2], [2, 1]],), "expect": [[0, 1], [1, 0]]},
    {"name": "all the same height", "args": ([[5] * 4 for _ in range(4)],)},
    {"name": "a bump in the middle", "args": ([[1, 1, 1], [1, 2, 1], [1, 1, 1]],)},
    {"name": "a peak in the middle", "args": (pyramid(5),)},
    {"name": "a bowl", "args": (basin(5),)},
    {"name": "rising towards the Atlantic", "args": (slope(5, 6),)},
    {"name": "rising towards the Pacific", "args": (slope(6, 5, towards_atlantic=False),)},
    {"name": "random 8 x 8, many plateaus", "args": (terrain(21, 8, 8, 3),)},
    {"name": "random 20 x 30", "args": (terrain(22, 20, 30, 9),)},
    {"name": "a 120 x 120 bowl", "args": (basin(120),), "limit_ms": 500},
    {"name": "an 80 x 80 slope", "args": (slope(80, 80),), "limit_ms": 500},
]


def reaches(heights, r0, c0, stop_early):
    """Follow the water from (r0, c0): (reaches the Pacific, reaches the Atlantic)."""
    rows, cols = len(heights), len(heights[0])
    seen, stack = {(r0, c0)}, [(r0, c0)]
    pacific = atlantic = False
    while stack:
        r, c = stack.pop()
        pacific = pacific or r == 0 or c == 0
        atlantic = atlantic or r == rows - 1 or c == cols - 1
        if stop_early and pacific and atlantic:
            break
        for dr, dc in STEPS:
            nr, nc = r + dr, c + dc
            if (
                0 <= nr < rows
                and 0 <= nc < cols
                and (nr, nc) not in seen
                and heights[nr][nc] <= heights[r][c]
            ):
                seen.add((nr, nc))
                stack.append((nr, nc))
    return pacific, atlantic


def brute(heights):
    """From every cell, search everywhere its water can flow, and keep the cells that touch
    both oceans."""
    return [
        [r, c]
        for r in range(len(heights))
        for c in range(len(heights[0]))
        if all(reaches(heights, r, c, stop_early=False))
    ]


def naive(heights):
    """The same search from every cell, stopping as soon as both oceans are found: the
    plausible version, still O((m * n)^2) when most cells reach at most one ocean."""
    return [
        [r, c]
        for r in range(len(heights))
        for c in range(len(heights[0]))
        if all(reaches(heights, r, c, stop_early=True))
    ]


def random_cases(rng: random.Random):
    for _ in range(300):
        rows, cols = rng.randint(1, 6), rng.randint(1, 6)
        high = rng.choice((1, 3, 9))
        yield ([[rng.randint(0, high) for _ in range(cols)] for _ in range(rows)],)
