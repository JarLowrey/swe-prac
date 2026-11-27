"""Tests for Product of Array Except Self. Expected outputs come from solution.py, checked against
brute()."""

import math
import random

SHOWN = [
    {"name": "Example 1", "args": ([1, 2, 3, 4],), "expect": [24, 12, 8, 6]},
    {"name": "Example 2", "args": ([-1, 1, 0, -3, 3],), "expect": [0, 0, 9, 0, 0]},
    {"name": "Example 3", "args": ([2, 3, 4],), "expect": [12, 8, 6]},
]


def mostly_ones(n: int, seed: int, zero: bool = False) -> list[int]:
    """n numbers that are mostly 1 and -1, with a few 2s and 3s, so every product stays small
    (and so does the expected output). Optionally one 0 in the middle."""
    rng = random.Random(seed)
    nums = [rng.choice((1, -1)) for _ in range(n)]
    for k, v in enumerate((2, -2, 3, 2, -3)):
        nums[(k + 1) * n // 7] = v
    if zero:
        nums[n // 2] = 0
    return nums


HIDDEN = [
    {"name": "empty array", "args": ([],), "expect": []},
    {"name": "one element", "args": ([5],), "expect": [1]},
    {"name": "two elements", "args": ([3, 4],), "expect": [4, 3]},
    {"name": "one zero", "args": ([1, 2, 0, 4],), "expect": [0, 0, 8, 0]},
    {"name": "two zeros", "args": ([0, 2, 0],), "expect": [0, 0, 0]},
    {"name": "zero first", "args": ([0, 4, 5],), "expect": [20, 0, 0]},
    {"name": "zero last", "args": ([4, 5, 0],), "expect": [0, 0, 20]},
    {"name": "negative numbers", "args": ([-1, 2, -3, 4],), "expect": [-24, 12, -8, 6]},
    {"name": "all ones", "args": ([1, 1, 1, 1],)},
    {"name": "all minus ones", "args": ([-1, -1, -1],)},
    {"name": "largest values", "args": ([30, -30, 2],), "expect": [-60, 60, -900]},
    {"name": "longer mix", "args": ([2, -1, 3, 1, -2, 1, 2],)},
    {"name": "20,000 numbers", "args": (mostly_ones(20_000, 8),), "limit_ms": 500},
    {
        "name": "20,000 numbers with one zero",
        "args": (mostly_ones(20_000, 9, zero=True),),
        "limit_ms": 500,
    },
]


def brute(nums):
    answer = []
    for i in range(len(nums)):
        product = 1
        for j in range(len(nums)):
            if j != i:
                product *= nums[j]
        answer.append(product)
    return answer


def naive(nums):
    """The O(n²) approach the large tests must reject, with the multiplying done in C by
    math.prod, so it is much faster than brute()."""
    return [math.prod(nums[:i]) * math.prod(nums[i + 1 :]) for i in range(len(nums))]


def random_cases(rng: random.Random):
    for _ in range(300):
        n = rng.randint(0, 9)
        yield ([rng.choice((-3, -2, -1, 0, 1, 1, 2, 3, 5)) for _ in range(n)],)
