"""Tests for Contains Duplicate. Expected outputs come from solution.py, checked against brute()."""

import random

SHOWN = [
    {"name": "Example 1", "args": ([1, 2, 2, 3, 4],), "expect": True},
    {"name": "Example 2", "args": ([1, 2, 3, 4],), "expect": False},
    {"name": "Example 3", "args": ([3, 1, 4, 1, 5, 9, 2, 6],), "expect": True},
]


def repeat_at_the_end(n: int) -> list[int]:
    """n - 1 distinct values, then a second copy of the last one. The only duplicate pair is the
    last two elements, so checking pairs from the front finds it after about n²/2 steps."""
    nums = list(range(n - 1))
    return nums + [nums[-1]]


def shuffled_distinct(n: int, seed: int) -> list[int]:
    """n distinct values in random order: nothing to find, so every pair gets checked."""
    nums = list(range(n))
    random.Random(seed).shuffle(nums)
    return nums


HIDDEN = [
    {"name": "empty array", "args": ([],), "expect": False},
    {"name": "one element", "args": ([7],), "expect": False},
    {"name": "two equal values", "args": ([5, 5],), "expect": True},
    {"name": "a value and its negative", "args": ([5, -5],), "expect": False},
    {"name": "all equal", "args": ([2, 2, 2, 2, 2],), "expect": True},
    {"name": "duplicate at both ends", "args": ([9, 1, 2, 3, 4, 9],), "expect": True},
    {"name": "duplicate is the last two", "args": ([4, 8, 15, 16, 23, 42, 42],), "expect": True},
    {"name": "negative duplicates", "args": ([-1, -2, -3, -2],), "expect": True},
    {"name": "distinct, with negatives and zero", "args": ([-3, 0, 3, -1, 1, 2, -2],)},
    {"name": "large values", "args": ([10**9, -(10**9), 999_999_999, -(10**9)],)},
    {
        "name": "16,000 numbers, the duplicate at the end",
        "args": (repeat_at_the_end(16_000),),
        "limit_ms": 500,
    },
    {
        "name": "16,000 distinct numbers",
        "args": (shuffled_distinct(16_000, 7),),
        "limit_ms": 500,
    },
]


def brute(nums):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] == nums[j]:
                return True
    return False


def naive(nums):
    """The plausible O(n²) shortcut the large tests must reject: search the rest of the array
    for each element. The search runs in C, so it is far faster than brute()."""
    return any(x in nums[i + 1 :] for i, x in enumerate(nums))


def random_cases(rng: random.Random):
    for _ in range(150):  # small range: duplicates are likely
        yield ([rng.randint(-5, 5) for _ in range(rng.randint(0, 8))],)
    for _ in range(150):  # distinct values, sometimes with one value copied
        nums = rng.sample(range(-50, 50), rng.randint(0, 10))
        if nums and rng.random() < 0.5:
            nums.insert(rng.randint(0, len(nums)), rng.choice(nums))
        yield (nums,)
