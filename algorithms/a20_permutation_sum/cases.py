"""Tests for Permutation Sum (count the ordered sequences of nums that add up to target).
Expected outputs come from solution.py, checked against brute()."""

import random

SHOWN = [
    {"name": "Example 1", "args": ([1, 2, 3], 4), "expect": 7},
    {"name": "Example 2", "args": ([9], 3), "expect": 0},
    {"name": "Example 3", "args": ([5, 3], 8), "expect": 2},
]

# Found by search: 35 numbers whose sequences adding up to 959 just fit in 32 bits.
THIRTY_FIVE = [
    57,
    61,
    74,
    83,
    93,
    105,
    110,
    129,
    144,
    145,
    157,
    164,
    173,
    207,
    223,
    254,
    278,
    285,
    288,
    294,
    297,
    305,
    307,
    334,
    350,
    355,
    367,
    388,
    393,
    413,
    424,
    432,
    434,
    435,
    439,
]

HIDDEN = [
    {"name": "one number, one way", "args": ([1], 1), "expect": 1},
    {"name": "the target is one of the numbers", "args": ([1000], 1000), "expect": 1},
    {"name": "1s and 2s", "args": ([1, 2], 10), "expect": 89},
    {"name": "unsorted numbers", "args": ([3, 1, 2], 4), "expect": 7},
    {"name": "even numbers, odd target", "args": ([2, 4, 6], 7), "expect": 0},
    {"name": "a 1 and a 50", "args": ([1, 50], 150), "expect": 1429},
    {"name": "large numbers", "args": ([10, 20, 30], 100), "expect": 274},
    {"name": "not a multiple", "args": ([7], 1000), "expect": 0},
    {"name": "1, 2 and 4", "args": ([4, 2, 1], 20)},
    # Without a memo the work is at least the answer itself (or, for the 0, every dead end).
    {
        "name": "two billion sequences",
        "args": ([1, 2, 3], 36),
        "expect": 2082876103,
        "limit_ms": 500,
    },
    {
        "name": "200 even numbers, odd target",
        "args": (list(range(2, 401, 2)), 999),
        "expect": 0,
        "limit_ms": 500,
    },
    {
        "name": "35 numbers, target 959",
        "args": (THIRTY_FIVE, 959),
        "expect": 1295123663,
        "limit_ms": 500,
    },
]


def brute(nums, target):
    """Grow every sequence one number at a time and count the ones that hit the target
    exactly. Each stack entry is the sum of one distinct sequence prefix (small inputs only)."""
    count = 0
    stack = [0]
    while stack:
        total = stack.pop()
        if total == target:
            count += 1
            continue
        for x in nums:
            if total + x <= target:
                stack.append(total + x)
    return count


def naive(nums, target):
    """The plain recursion without a memo: exponential, so the large tests must reject it."""

    def count(left):
        if left == 0:
            return 1
        return sum(count(left - x) for x in nums if x <= left)

    return count(target)


def random_cases(rng: random.Random):
    for _ in range(300):
        nums = rng.sample(range(1, 9), rng.randint(1, 4))
        yield nums, rng.randint(1, 14)
