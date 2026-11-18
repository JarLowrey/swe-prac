"""Tests for House Robber. Expected outputs come from solution.py, checked against brute()."""

import random

SHOWN = [
    {"name": "Example 1", "args": ([1, 2, 3, 1],), "expect": 4},
    {"name": "Example 2", "args": ([2, 7, 9, 3, 1],), "expect": 12},
    {"name": "Example 3", "args": ([2, 1, 1, 2],), "expect": 4},
]

HIDDEN = [
    {"name": "one house", "args": ([5],), "expect": 5},
    {"name": "two houses: the richer one", "args": ([3, 10],), "expect": 10},
    {"name": "empty houses", "args": ([0, 0, 0],), "expect": 0},
    {"name": "richest house first is wrong", "args": ([2, 3, 2],), "expect": 4},
    {"name": "both ends", "args": ([5, 1, 1, 5],), "expect": 10},
    {"name": "increasing amounts", "args": ([1, 2, 3, 4, 5, 6],), "expect": 12},
    {"name": "all equal", "args": ([4, 4, 4, 4, 4],), "expect": 12},
    {"name": "skip two in a row, twice", "args": ([400, 0, 0, 400, 0, 0, 400],), "expect": 1200},
    {"name": "the last house decides", "args": ([1, 3, 1, 3, 100],), "expect": 103},
    {"name": "seven houses", "args": ([6, 7, 1, 30, 8, 2, 4],), "expect": 41},
    # The plain recursion makes about 1.6^n calls: 100 houses never finish without a memo.
    {
        "name": "100 random houses",
        "args": ([random.Random(33).randint(0, 400) for _ in range(100)],),
        "limit_ms": 500,
    },
    {
        "name": "100 houses, rob every third",
        "args": ([400, 0, 0] * 33 + [400],),
        "expect": 13600,
        "limit_ms": 500,
    },
]


def brute(nums):
    """Try every set of houses (a bit mask) with no two adjacent ones (small inputs only)."""
    n = len(nums)
    best = 0
    for mask in range(1 << n):
        if mask & (mask >> 1) == 0:  # no two neighbouring bits set
            best = max(best, sum(nums[i] for i in range(n) if mask >> i & 1))
    return best


def naive(nums):
    """The plain rob-or-skip recursion without a memo: exponential."""

    def best(i):
        if i >= len(nums):
            return 0
        return max(nums[i] + best(i + 2), best(i + 1))

    return best(0)


def random_cases(rng: random.Random):
    for _ in range(300):
        n = rng.randint(1, 12)
        yield ([rng.randint(0, 400) for _ in range(n)],)
