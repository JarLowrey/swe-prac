"""Tests for Non-overlapping Intervals. Expected outputs come from solution.py, checked against
brute() (every subset, so the hidden tests without a time limit stay small)."""

import random
from itertools import pairwise

SHOWN = [
    {"name": "Example 1", "args": ([[1, 3], [2, 5], [4, 6]],), "expect": 1},
    {"name": "Example 2", "args": ([[1, 2], [1, 2], [1, 2]],), "expect": 2},
    {"name": "Example 3", "args": ([[1, 2], [2, 3]],), "expect": 0},
]


def short_meetings(n: int, seed: int) -> list[list[int]]:
    """n short random intervals packed into a range of 10,000: many overlaps, many survivors."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        start = rng.randint(0, 9_970)
        out.append([start, start + rng.randint(1, 30)])
    return out


def touching_chain(n: int, seed: int) -> list[list[int]]:
    """[0,1], [1,2], ... shuffled: every interval can stay, so the O(n²) DP finds a
    compatible earlier interval at every step and does the most work."""
    out = [[i, i + 1] for i in range(n)]
    random.Random(seed).shuffle(out)
    return out


def nested(n: int) -> list[list[int]]:
    """n intervals nested like dolls, in a scrambled order: only one can stay."""
    out = [[-i, i + 1] for i in range(n)]
    random.Random(17).shuffle(out)
    return out


HIDDEN = [
    {"name": "empty input", "args": ([],), "expect": 0},
    {"name": "one interval", "args": ([[3, 8]],), "expect": 0},
    {"name": "touching chain", "args": ([[3, 4], [1, 2], [4, 5], [2, 3]],), "expect": 0},
    {
        "name": "one long interval over short ones",
        "args": ([[1, 10], [2, 3], [4, 5], [6, 7]],),
        "expect": 1,
    },
    {
        "name": "the shortest interval is the wrong one to keep",
        "args": ([[1, 5], [4, 6], [5, 10]],),
        "expect": 1,
    },
    {
        "name": "four overlapping intervals",
        "args": ([[1, 2], [2, 3], [3, 4], [1, 3]],),
        "expect": 1,
    },
    {"name": "nested and crossing", "args": ([[1, 100], [11, 22], [1, 11], [2, 12]],), "expect": 2},
    {"name": "negative values", "args": ([[-5, -3], [-4, 0], [0, 2], [-10, -6]],)},
    {"name": "all share one moment", "args": ([[1, 5], [2, 6], [3, 7], [4, 8]],), "expect": 3},
    {"name": "same start, different ends", "args": ([[1, 4], [1, 2], [1, 3]],), "expect": 2},
    {"name": "unsorted mix", "args": ([[5, 7], [1, 3], [3, 5], [2, 4], [6, 8]],)},
    {"name": "wide range", "args": ([[-50_000, 50_000], [-50_000, -49_999], [49_999, 50_000]],)},
    {"name": "nested like dolls", "args": (nested(9),), "expect": 8},
    {"name": "7,000 short intervals", "args": (short_meetings(7_000, 23),), "limit_ms": 500},
    {"name": "6,000 touching intervals", "args": (touching_chain(6_000, 29),), "limit_ms": 500},
]


def brute(intervals):
    """Try every subset; keep the largest one with no overlaps."""
    n = len(intervals)
    best = 0
    for mask in range(1 << n):
        chosen = sorted(intervals[i] for i in range(n) if mask >> i & 1)
        # Sorted by start, a set has no overlaps exactly when each interval ends at or before
        # the next one starts.
        if all(a[1] <= b[0] for a, b in pairwise(chosen)):
            best = max(best, len(chosen))
    return n - best


def naive(intervals):
    """The O(n²) DP the large tests must reject: best[i] = the most intervals kept when
    interval i is the last one kept."""
    ordered = sorted(intervals)
    best = [1] * len(ordered)
    for i in range(len(ordered)):
        for j in range(i):
            if ordered[j][1] <= ordered[i][0] and best[j] + 1 > best[i]:
                best[i] = best[j] + 1
    return len(ordered) - max(best, default=0)


def random_cases(rng: random.Random):
    for _ in range(300):
        intervals = []
        for _ in range(rng.randint(0, 9)):
            start = rng.randint(-8, 8)
            intervals.append([start, start + rng.randint(1, 6)])
        yield (intervals,)
