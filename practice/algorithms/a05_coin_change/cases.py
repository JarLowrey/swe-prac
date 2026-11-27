"""Tests for Coin Change. Expected outputs come from solution.py, checked against brute()."""

import math
import random

SHOWN = [
    {"name": "Example 1", "args": ([1, 2, 5], 11), "expect": 3},
    {"name": "Example 2", "args": ([2], 3), "expect": -1},
    {"name": "Example 3", "args": ([1], 0), "expect": 0},
]

TWELVE_COINS = [1, 7, 13, 29, 41, 53, 67, 89, 97, 101, 103, 107]

HIDDEN = [
    {"name": "coin bigger than the amount", "args": ([2], 1), "expect": -1},
    {"name": "one coin, several times", "args": ([3], 9), "expect": 3},
    {"name": "biggest coin first is not best", "args": ([1, 3, 4], 6), "expect": 2},
    {"name": "biggest coin first gets stuck", "args": ([2, 5], 6), "expect": 3},
    {"name": "impossible with small coins", "args": ([3, 7], 11), "expect": -1},
    {"name": "unsorted coins", "args": ([5, 2, 1], 13), "expect": 4},
    {"name": "a huge coin", "args": ([2147483647], 2), "expect": -1},
    {"name": "a huge coin and a 1", "args": ([1, 2147483647], 2), "expect": 2},
    {"name": "10,000 coins of 1", "args": ([1], 10_000), "expect": 10_000},
    # Plain recursion branches on every coin at every step: these never finish without a memo.
    {
        "name": "4 coins, amount 6,249",
        "args": ([186, 419, 83, 408], 6249),
        "expect": 20,
        "limit_ms": 500,
    },
    {"name": "12 coins, amount 10,000", "args": (TWELVE_COINS, 10_000), "limit_ms": 500},
    # 9,999 is not a multiple of 7: every path is a dead end, so failures must be cached too.
    {"name": "impossible amount 9,999", "args": ([7, 14, 21], 9999), "expect": -1, "limit_ms": 500},
]


def brute(coins, amount):
    """Try every count of every coin (small amounts only): the last coin's count is forced."""
    best = math.inf

    def go(i, left, used):
        nonlocal best
        if i == len(coins) - 1:
            if left % coins[i] == 0:
                best = min(best, used + left // coins[i])
            return
        for k in range(left // coins[i] + 1):
            go(i + 1, left - k * coins[i], used + k)

    go(0, amount, 0)
    return -1 if best == math.inf else best


def naive(coins, amount):
    """The plain recursion without a memo: exponential, so the large tests must reject it."""

    def fewest(left):
        if left == 0:
            return 0
        best = math.inf
        for c in coins:
            if c <= left:
                best = min(best, 1 + fewest(left - c))
        return best

    best = fewest(amount)
    return -1 if best == math.inf else best


def random_cases(rng: random.Random):
    for _ in range(300):
        coins = rng.sample(range(1, 16), rng.randint(1, 4))
        yield coins, rng.randint(0, 40)
