"""Tests for Insert Interval. Expected outputs come from solution.py, checked against brute()."""

import random

SHOWN = [
    {"name": "Example 1", "args": ([[1, 3], [6, 9]], [2, 5]), "expect": [[1, 5], [6, 9]]},
    {
        "name": "Example 2",
        "args": ([[1, 2], [3, 5], [6, 7], [8, 10], [12, 16]], [4, 8]),
        "expect": [[1, 2], [3, 10], [12, 16]],
    },
    {
        "name": "Example 3",
        "args": ([[0, 1], [2, 3], [4, 5], [6, 7]], [2, 4]),
        "expect": [[0, 1], [2, 5], [6, 7]],
    },
]


def spaced(n: int) -> list[list[int]]:
    """[0,1], [2,3], [4,5], ...: sorted, and no two touch."""
    return [[2 * i, 2 * i + 1] for i in range(n)]


HIDDEN = [
    {"name": "no intervals yet", "args": ([], [5, 7]), "expect": [[5, 7]]},
    {"name": "goes before everything", "args": ([[3, 5], [8, 9]], [0, 1])},
    {"name": "goes after everything", "args": ([[1, 2], [3, 4]], [6, 8])},
    {"name": "fits in a gap", "args": ([[1, 2], [8, 9]], [4, 5])},
    {"name": "touches on the left", "args": ([[1, 3], [6, 8]], [3, 4]), "expect": [[1, 4], [6, 8]]},
    {
        "name": "touches on the right",
        "args": ([[1, 3], [6, 8]], [4, 6]),
        "expect": [[1, 3], [4, 8]],
    },
    {"name": "bridges two intervals", "args": ([[0, 5], [6, 10]], [5, 6]), "expect": [[0, 10]]},
    {"name": "covers everything", "args": ([[2, 3], [5, 6], [8, 9]], [1, 10]), "expect": [[1, 10]]},
    {"name": "inside one interval", "args": ([[1, 10]], [3, 4]), "expect": [[1, 10]]},
    {"name": "a single point in a gap", "args": ([[1, 3], [5, 7]], [4, 4])},
    {"name": "a single point on an end", "args": ([[1, 3], [5, 7]], [7, 7])},
    {
        "name": "starts inside one, ends inside another",
        "args": ([[1, 3], [5, 7], [9, 12]], [2, 10]),
    },
    {"name": "starts before the first, ends inside it", "args": ([[3, 5], [7, 9]], [1, 4])},
    {
        "name": "6,000 intervals, 4,000 of them merged",
        "args": (spaced(6_000), [2_001, 10_000]),
        "limit_ms": 500,
    },
    {
        "name": "7,000 points, the new interval after them all",
        "args": ([[i, i] for i in range(7_000)], [7_005, 7_010]),
        "limit_ms": 500,
    },
]


def brute(intervals, newInterval):
    """Add the new interval, then merge any two overlapping intervals until none overlap. Also
    the too-slow approach the large tests reject (no naive() needed)."""
    out = [list(iv) for iv in intervals] + [list(newInterval)]
    changed = True
    while changed:
        changed = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                a, b = out[i], out[j]
                if a[0] <= b[1] and b[0] <= a[1]:  # they share a point
                    out[i] = [min(a[0], b[0]), max(a[1], b[1])]
                    del out[j]
                    changed = True
                    break
            if changed:
                break
    return sorted(out)


def random_cases(rng: random.Random):
    for _ in range(300):
        intervals, at = [], rng.randint(0, 3)
        for _ in range(rng.randint(0, 7)):
            start = at
            end = start + rng.randint(0, 3)
            intervals.append([start, end])
            at = end + rng.randint(1, 3)  # the next one starts after this ends: no touching
        start = rng.randint(0, at + 2)
        yield (intervals, [start, start + rng.randint(0, 8)])
