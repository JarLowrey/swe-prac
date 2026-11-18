"""Tests for Climbing Stairs. Expected outputs come from solution.py, checked against brute()."""

import math
import random

SHOWN = [
    {"name": "Example 1", "args": (2,), "expect": 2},
    {"name": "Example 2", "args": (3,), "expect": 3},
    {"name": "Example 3", "args": (4,), "expect": 5},
]

HIDDEN = [
    {"name": "one step", "args": (1,), "expect": 1},
    {"name": "five steps", "args": (5,), "expect": 8},
    {"name": "six steps", "args": (6,), "expect": 13},
    {"name": "ten steps", "args": (10,), "expect": 89},
    {"name": "twenty steps", "args": (20,), "expect": 10946},
    {"name": "twenty-five steps", "args": (25,)},
    # Plain recursion makes about 2 * ways(n) calls: 30 million at n = 35, 3.7 billion at n = 45.
    {"name": "35 steps", "args": (35,), "limit_ms": 500},
    {"name": "45 steps", "args": (45,), "expect": 1836311903, "limit_ms": 500},
]


def brute(n):
    """Count by the number of 2-steps k: the climb has n - k moves, and choosing which k of them
    are the 2-steps gives C(n - k, k) different sequences."""
    return sum(math.comb(n - k, k) for k in range(n // 2 + 1))


def naive(n):
    """The plain recursion without a memo: exponential, so the large tests must reject it."""
    if n <= 1:
        return 1
    return naive(n - 1) + naive(n - 2)


def random_cases(rng: random.Random):
    # The whole input range is small enough to check every n.
    for n in range(1, 46):
        yield (n,)
