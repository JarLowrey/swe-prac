"""Tests for Two Sum. Expected outputs come from solution.py, checked against brute()."""

import random

SHOWN = [
    {"name": "Example 1", "args": ([2, 7, 11, 15], 9), "expect": [0, 1]},
    {"name": "Example 2", "args": ([3, 2, 4], 6), "expect": [1, 2]},
    {"name": "Example 3", "args": ([3, 3], 6), "expect": [0, 1]},
]


def unique_pair(rng: random.Random, n: int, low: int, high: int) -> tuple[list[int], int]:
    """n numbers in [low, high] where exactly one pair sums to the target."""
    while True:
        nums = [rng.randint(low, high) for _ in range(n)]
        i, j = rng.sample(range(n), 2)
        target = nums[i] + nums[j]
        if count_pairs(nums, target) == 1:
            return nums, target


def count_pairs(nums: list[int], target: int) -> int:
    counts: dict[int, int] = {}
    pairs = 0
    for x in nums:
        pairs += counts.get(target - x, 0)
        counts[x] = counts.get(x, 0) + 1
    return pairs


def answer_at_the_end(n: int) -> tuple[list[int], int]:
    """Distinct even numbers, then two odd ones: the only pair summing to an odd target is the
    last two elements, so checking pairs from the front takes all n²/2 steps."""
    nums = [2 * i for i in range(n - 2)] + [10**9 + 1, 10**9 + 3]
    return nums, 2 * 10**9 + 4


HIDDEN = [
    {"name": "smallest input", "args": ([1, 2], 3)},
    {"name": "equal values", "args": ([1, 1], 2)},
    {"name": "negative numbers", "args": ([-2, 0, 4], 2)},
    {"name": "target zero", "args": ([-3, 4, 3, 90], 0)},
    {"name": "answer at both ends", "args": ([5, 1, 2, 3, 4, 6], 11)},
    {"name": "can't reuse an element", "args": ([5, 75, 25], 100)},
    {"name": "duplicates elsewhere", "args": ([2, 2, 2, 9, 4], 13)},
    {"name": "large values", "args": ([10**9, -(10**9), 3, 10**9 - 1], 2 * 10**9 - 1)},
    {"name": "answer at the end", "args": (list(range(1, 50)) + [1000], 1049)},
    {"name": "20,000 numbers", "args": answer_at_the_end(20_000), "limit_ms": 500},
    {
        "name": "20,000 random numbers",
        "args": unique_pair(random.Random(7), 20_000, -(10**9), 10**9),
        "limit_ms": 500,
    },
]


def brute(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []


def random_cases(rng: random.Random):
    for _ in range(300):
        yield unique_pair(rng, rng.randint(2, 12), -20, 20)
