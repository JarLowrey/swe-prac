"""Tests for Longest Consecutive Sequence. Expected outputs come from solution.py, checked against
brute()."""

import random

SHOWN = [
    {"name": "Example 1", "args": ([100, 4, 200, 1, 3, 2],), "expect": 4},
    {"name": "Example 2", "args": ([0, 3, 7, 2, 5, 8, 4, 6, 0, 1],), "expect": 9},
    {"name": "Example 3", "args": ([1, 5, 2, 7],), "expect": 2},
]


def one_long_run(low: int, high: int, seed: int) -> list[int]:
    """Every value from low to high, shuffled: walking upwards from every value (not just from
    starts) takes about n²/2 steps."""
    nums = list(range(low, high + 1))
    random.Random(seed).shuffle(nums)
    return nums


def repeated_start(k: int, seed: int) -> list[int]:
    """k copies of 0 and then 1..k-1, shuffled: looping over nums instead of the set walks the
    run of length k once per copy of its start, k² steps."""
    nums = [0] * k + list(range(1, k))
    random.Random(seed).shuffle(nums)
    return nums


HIDDEN = [
    {"name": "empty array", "args": ([],), "expect": 0},
    {"name": "one number", "args": ([7],), "expect": 1},
    {"name": "all the same", "args": ([5, 5, 5],), "expect": 1},
    {"name": "duplicates inside a run", "args": ([1, 2, 2, 2, 3, 4],), "expect": 4},
    {"name": "negative numbers", "args": ([-3, -1, -2, 0, 5],), "expect": 4},
    {"name": "a run across zero", "args": ([-2, 2, -1, 1, 0],), "expect": 5},
    {"name": "no two consecutive", "args": ([1, 3, 5, 7],), "expect": 1},
    {"name": "the longer run comes second", "args": ([10, 5, 11, 3, 12, 4, 1, 13, 2],)},
    {"name": "descending order", "args": ([5, 4, 3, 2, 1],), "expect": 5},
    {"name": "two runs of the same length", "args": ([1, 2, 10, 11],), "expect": 2},
    {"name": "extreme values", "args": ([-(10**9), 10**9, 10**9 - 1],), "expect": 2},
    {
        "name": "15,000 numbers in one run",
        "args": (one_long_run(-7000, 7999, 11),),
        "limit_ms": 500,
    },
    {
        "name": "a run's start repeated 10,000 times",
        "args": (repeated_start(10_000, 12),),
        "limit_ms": 500,
    },
]


def brute(nums):
    values = sorted(set(nums))
    best = run = 0
    for i, x in enumerate(values):
        run = run + 1 if i > 0 and x == values[i - 1] + 1 else 1
        best = max(best, run)
    return best


def naive(nums):
    """The O(n²) approach the large tests must reject: walk upwards from every value, not only
    from the start of each run."""
    values = set(nums)
    best = 0
    for x in values:
        end = x
        while end + 1 in values:
            end += 1
        best = max(best, end - x + 1)
    return best


def random_cases(rng: random.Random):
    for _ in range(300):
        n = rng.randint(0, 12)
        low = rng.randint(-15, 5)
        yield ([rng.randint(low, low + 12) for _ in range(n)],)
