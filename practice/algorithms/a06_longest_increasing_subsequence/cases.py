"""Tests for Longest Increasing Subsequence. Expected outputs come from solution.py, checked
against brute()."""

import random
from itertools import combinations

SHOWN = [
    {"name": "Example 1", "args": ([10, 9, 2, 5, 3, 7, 101, 18],), "expect": 4},
    {"name": "Example 2", "args": ([0, 1, 0, 3, 2, 3],), "expect": 4},
    {"name": "Example 3", "args": ([7, 7, 7, 7, 7, 7, 7],), "expect": 1},
]


def rising_with_noise(seed: int, n: int) -> list[int]:
    """An upward trend with noise: a long answer, and astronomically many increasing
    subsequences for the take-or-skip recursion to walk through."""
    rng = random.Random(seed)
    return [-10_000 + 40 * i + rng.randint(-100, 100) for i in range(n)]


def random_values(seed: int, n: int) -> list[int]:
    rng = random.Random(seed)
    return [rng.randint(-10_000, 10_000) for _ in range(n)]


HIDDEN = [
    {"name": "one number", "args": ([5],), "expect": 1},
    {"name": "strictly decreasing", "args": ([5, 4, 3, 2, 1],), "expect": 1},
    {"name": "already increasing", "args": ([1, 2, 3, 4, 5],), "expect": 5},
    {"name": "equal values don't extend a run", "args": ([2, 2, 3],), "expect": 2},
    {"name": "skip a dip", "args": ([1, 2, 3, 0, 5],), "expect": 4},
    {"name": "a big early value is a trap", "args": ([1, 5, 2, 3],), "expect": 3},
    {"name": "ends before the last element", "args": ([1, 2, 0],), "expect": 2},
    {"name": "repeated values", "args": ([4, 10, 4, 3, 8, 9],), "expect": 3},
    {"name": "nine numbers", "args": ([1, 3, 6, 7, 9, 4, 10, 5, 6],), "expect": 6},
    {"name": "extreme values", "args": ([-10_000, 10_000, -9_999, 9_999],), "expect": 3},
    {"name": "eleven numbers", "args": ([3, 5, 6, 2, 5, 4, 19, 5, 6, 7, 12],)},
    # The take-or-skip recursion without a memo never finishes on these. 400 numbers keeps
    # every O(n^2) solution comfortably inside the limit, memo on (prev, i) included.
    {"name": "400 numbers, rising", "args": (rising_with_noise(6, 400),), "limit_ms": 500},
    {"name": "400 random numbers", "args": (random_values(66, 400),), "limit_ms": 500},
]


def brute(nums):
    """Try subsets from the largest size down; the first strictly increasing one wins."""
    for size in range(len(nums), 0, -1):
        for chosen in combinations(nums, size):  # keeps the original order
            if all(a < b for a, b in zip(chosen, chosen[1:], strict=False)):
                return size
    return 0


def naive(nums):
    """Take or skip each element, remembering the last one taken, with no memo: exponential."""

    def longest(prev, i):
        if i == len(nums):
            return 0
        skip = longest(prev, i + 1)
        take = 0
        if prev == -1 or nums[prev] < nums[i]:
            take = 1 + longest(i, i + 1)
        return max(skip, take)

    return longest(-1, 0)


def random_cases(rng: random.Random):
    for _ in range(300):
        n = rng.randint(1, 11)
        yield ([rng.randint(-5, 5) for _ in range(n)],)
