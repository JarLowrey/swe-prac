"""Tests for Merge Intervals. Expected outputs come from solution.py, checked against brute().
The answer may list the merged intervals in any order ("compare": "unordered")."""

import random

SHOWN = [
    {
        "name": "Example 1",
        "args": ([[1, 3], [2, 6], [8, 10], [15, 18]],),
        "expect": [[1, 6], [8, 10], [15, 18]],
    },
    {"name": "Example 2", "args": ([[1, 4], [4, 5]],), "expect": [[1, 5]]},
    {"name": "Example 3", "args": ([[5, 10], [1, 4], [2, 7]],), "expect": [[1, 10]]},
]


def separate_points(n: int, seed: int) -> list[list[int]]:
    """n single points [i, i], shuffled: nothing overlaps, so a pass over every pair finds no
    merge at all and does all n²/2 comparisons."""
    points = [[i, i] for i in range(n)]
    random.Random(seed).shuffle(points)
    return points


def loners_then_chain(loners: int, chain: int, seed: int) -> list[list[int]]:
    """First `loners` separate points that overlap nothing, then [0,1], [1,2], ...,
    [chain-1, chain] shuffled, which all merge into [0, chain]. The merges are at the end of
    the list, so an approach that merges one pair and rescans from the front repeats the
    loners' comparisons for every merge."""
    rng = random.Random(seed)
    alone = [[chain + 1000 + 2 * i, chain + 1000 + 2 * i] for i in range(loners)]
    links = [[i, i + 1] for i in range(chain)]
    rng.shuffle(alone)
    rng.shuffle(links)
    return alone + links


HIDDEN = [
    {"name": "empty input", "args": ([],), "expect": []},
    {"name": "one interval", "args": ([[5, 7]],), "expect": [[5, 7]]},
    {"name": "touching chain", "args": ([[3, 4], [1, 2], [2, 3]],), "expect": [[1, 4]]},
    {"name": "nested intervals", "args": ([[1, 10], [2, 3], [4, 5]],), "expect": [[1, 10]]},
    {"name": "shorter interval after a longer one", "args": ([[1, 4], [2, 3]],)},
    {"name": "neighbours that don't touch", "args": ([[1, 2], [3, 4]],)},
    {"name": "duplicates", "args": ([[1, 3], [1, 3], [1, 3]],)},
    {"name": "single points", "args": ([[2, 2], [1, 1], [2, 2], [3, 5]],)},
    {"name": "a point on an end", "args": ([[1, 4], [4, 4], [0, 0]],)},
    {"name": "wide interval sorted last by end", "args": ([[2, 3], [4, 5], [6, 7], [1, 10]],)},
    {"name": "reverse order, no overlaps", "args": ([[10, 11], [7, 9], [4, 6], [1, 3]],)},
    {"name": "everything overlaps, unsorted", "args": ([[3, 9], [0, 2], [1, 5], [8, 12]],)},
    {"name": "zeros", "args": ([[0, 0], [0, 0]],)},
    {"name": "7,000 separate points", "args": (separate_points(7_000, 16),), "limit_ms": 500},
    {
        "name": "2,000 separate intervals, then a chain of 4,000",
        "args": (loners_then_chain(2_000, 4_000, 61),),
        "limit_ms": 500,
    },
]


def brute(intervals):
    """Merge any two overlapping intervals into their union, until no two overlap. Also the
    too-slow approach the large tests reject (no naive() needed)."""
    out = [list(iv) for iv in intervals]
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
        n = rng.randint(0, 9)
        intervals = []
        for _ in range(n):
            start = rng.randint(0, 20)
            intervals.append([start, start + rng.randint(0, 5)])
        yield (intervals,)
