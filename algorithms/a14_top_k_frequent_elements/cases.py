"""Tests for Top K Frequent Elements. The values may come back in any order
("compare": "unordered"). Every case has a unique answer: the k-th most frequent value appears
strictly more often than the next one. Expected outputs come from solution.py, checked against
brute()."""

import random
from collections import Counter

SHOWN = [
    {"name": "Example 1", "args": ([1, 1, 1, 2, 2, 3], 2), "expect": [1, 2]},
    {"name": "Example 2", "args": ([1], 1), "expect": [1]},
    {"name": "Example 3", "args": ([4, 1, -1, 2, -1, 2, 3], 2), "expect": [-1, 2]},
]


def doubles_and_singles(seed: int) -> tuple[list[int], int]:
    """3,000 values that appear twice among 11,000 that appear once (17,000 numbers, k = 3,000).
    Calling nums.count for each of the 14,000 distinct values is far too slow."""
    rng = random.Random(seed)
    values = rng.sample(range(-(10**4), 10**4 + 1), 14_000)
    nums = values[:3000] * 2 + values[3000:]
    rng.shuffle(nums)
    return nums, 3000


def a_few_popular(seed: int) -> tuple[list[int], int]:
    """Ten values that appear 12 to 21 times, hidden among 15,800 values that appear once."""
    rng = random.Random(seed)
    values = rng.sample(range(-(10**4), 10**4 + 1), 15_810)
    nums = values[10:]
    for i, v in enumerate(values[:10]):
        nums += [v] * (12 + i)
    rng.shuffle(nums)
    return nums, 10


def staircase() -> list[int]:
    """1 once, 2 twice, ... 5 five times, interleaved."""
    nums = [v for v in range(1, 6) for _ in range(v)]
    random.Random(4).shuffle(nums)
    return nums


HIDDEN = [
    {"name": "all the same value", "args": ([3, 3, 3], 1), "expect": [3]},
    {"name": "k is every distinct value", "args": ([1, 2, 2, 3, 3, 3], 3), "expect": [1, 2, 3]},
    {"name": "the most frequent comes last", "args": ([1, 2, 3, 4, 4, 4], 1), "expect": [4]},
    {"name": "negative values", "args": ([-1, -1, -2, -2, -2, 4], 2), "expect": [-2, -1]},
    {"name": "zero is the most frequent", "args": ([0, 0, 0, 1, 1, 2], 2), "expect": [0, 1]},
    {"name": "ties below the cut", "args": ([5, 5, 5, 6, 6, 7, 8, 9], 2), "expect": [5, 6]},
    {"name": "ties inside the answer", "args": ([1, 1, 2, 2, 3], 2), "expect": [1, 2]},
    {"name": "counts 1 to 5", "args": (staircase(), 3), "expect": [5, 4, 3]},
    {"name": "extreme values", "args": ([10**4, -(10**4), 10**4], 1), "expect": [10**4]},
    {"name": "one value, many times", "args": ([7] * 50 + [8], 1), "expect": [7]},
    {"name": "17,000 numbers, k = 3,000", "args": doubles_and_singles(14), "limit_ms": 500},
    {"name": "16,000 numbers, ten popular", "args": a_few_popular(15), "limit_ms": 500},
]


def brute(nums, k):
    counts = Counter(nums)
    ranked = sorted(counts, key=lambda v: -counts[v])
    return ranked[:k]


def naive(nums, k):
    """The O(n²) one-liner the large tests must reject: nums.count rescans the whole array for
    every distinct value."""
    return sorted(set(nums), key=nums.count, reverse=True)[:k]


def random_cases(rng: random.Random):
    """Random arrays with k chosen where the answer is unique (or k = every distinct value)."""
    for _ in range(300):
        nums = [rng.randint(-4, 6) for _ in range(rng.randint(1, 14))]
        counts = sorted(Counter(nums).values(), reverse=True)
        cuts = [k for k in range(1, len(counts)) if counts[k - 1] > counts[k]]
        yield (nums, rng.choice(cuts + [len(counts)]))
