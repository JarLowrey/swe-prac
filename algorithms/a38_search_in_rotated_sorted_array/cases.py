"""Tests for Search in Rotated Sorted Array. Expected outputs come from solution.py, checked
against brute(), a linear scan.

There is no time-limited test: a linear scan of the largest allowed input (5,000 values) takes
well under a millisecond, so no fair limit separates O(n) from O(log n). The large cases check
correctness on long ranges instead."""

import random


def rotate(values: list[int], k: int) -> list[int]:
    """values rotated at index k: values[k:] moves to the front."""
    return values[k:] + values[:k]


SHOWN = [
    {"name": "Example 1", "args": ([4, 5, 6, 7, 0, 1, 2], 0), "expect": 4},
    {"name": "Example 2", "args": ([4, 5, 6, 7, 0, 1, 2], 3), "expect": -1},
    {"name": "Example 3", "args": ([1], 0), "expect": -1},
]

# 5,000 distinct values rotated at index 3,217: the second run starts at index 1,783.
BIG = rotate(sorted(random.Random(38).sample(range(-10_000, 10_001), 5000)), 3217)
# The first value above nums[0] that isn't in BIG: absent, inside the first run's range.
_present = set(BIG)
MISSING = next(v for v in range(BIG[0] + 1, 10_001) if v not in _present)

HIDDEN = [
    {"name": "one element, found", "args": ([5], 5), "expect": 0},
    {"name": "two elements, the smaller one", "args": ([3, 1], 1), "expect": 1},
    {"name": "not rotated", "args": ([1, 3, 5, 7, 9, 11], 9), "expect": 4},
    {"name": "not rotated, smaller than everything", "args": ([2, 4, 6, 8], 1), "expect": -1},
    {"name": "target is the smallest value", "args": ([5, 6, 7, 1, 2, 3, 4], 1), "expect": 3},
    {"name": "target is the largest value", "args": ([5, 6, 7, 1, 2, 3, 4], 7), "expect": 2},
    {"name": "target is nums[0]", "args": ([6, 7, 1, 2, 3, 4, 5], 6), "expect": 0},
    {"name": "target is the last element", "args": ([6, 7, 1, 2, 3, 4, 5], 5), "expect": 6},
    {"name": "only the largest value moved", "args": ([9, 1, 2, 3, 4, 5, 6, 7, 8], 8), "expect": 8},
    {"name": "only the smallest value left", "args": ([2, 3, 4, 5, 6, 7, 8, 9, 1], 1), "expect": 8},
    {"name": "negatives, absent", "args": ([-3, -1, 2, -10, -7], -5), "expect": -1},
    {"name": "larger than everything", "args": ([30, 40, 50, 10, 20], 60), "expect": -1},
    {"name": "5,000 values, the largest", "args": (BIG, BIG[1782]), "expect": 1782},
    {"name": "5,000 values, absent", "args": (BIG, MISSING), "expect": -1},
]


def brute(nums, target):
    for i, x in enumerate(nums):
        if x == target:
            return i
    return -1


def random_cases(rng: random.Random):
    for _ in range(400):
        n = rng.randint(1, 10)
        nums = rotate(sorted(rng.sample(range(-20, 21), n)), rng.randrange(n))
        # Usually a value from the array, sometimes any value (often absent).
        target = rng.choice(nums) if rng.random() < 0.6 else rng.randint(-22, 22)
        yield (nums, target)
