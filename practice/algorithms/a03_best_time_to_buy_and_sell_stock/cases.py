"""Tests for Best Time to Buy and Sell Stock. Expected outputs come from solution.py, checked
against brute()."""

import random

SHOWN = [
    {"name": "Example 1", "args": ([7, 1, 5, 3, 6, 4],), "expect": 5},
    {"name": "Example 2", "args": ([7, 6, 4, 3, 1],), "expect": 0},
    {"name": "Example 3", "args": ([3, 2, 1, 4],), "expect": 3},
]


def peak_first_low_last(n: int, seed: int) -> list[int]:
    """The highest price on day 0 and the lowest on the last day, so max - min is wrong; the
    real answer is hidden in the middle."""
    rng = random.Random(seed)
    return [99] + [rng.randint(20, 80) for _ in range(n - 2)] + [1]


def falling(n: int) -> list[int]:
    """Prices that never rise (from 99 down to 1): the answer is 0, and nothing stops a pairwise
    search early."""
    return [99 - (i * 99) // n for i in range(n)]


HIDDEN = [
    {"name": "no days", "args": ([],), "expect": 0},
    {"name": "one day", "args": ([5],), "expect": 0},
    {"name": "two days, rising", "args": ([1, 2],), "expect": 1},
    {"name": "two days, falling", "args": ([2, 1],), "expect": 0},
    {"name": "flat prices", "args": ([3, 3, 3, 3],), "expect": 0},
    {"name": "the lowest price comes last", "args": ([5, 9, 1],), "expect": 4},
    {"name": "the best trade skips the lowest price", "args": ([3, 8, 1, 2],), "expect": 5},
    {"name": "a later low gives a bigger rise", "args": ([4, 7, 1, 9],), "expect": 8},
    {"name": "buy on the first day, sell on the last", "args": ([1, 5, 3, 6, 2, 10],)},
    {"name": "prices of zero", "args": ([6, 0, 0, 6, 0],)},
    {"name": "many small rises", "args": ([10, 1, 2, 1, 2, 1, 3, 2],)},
    {"name": "largest prices", "args": ([10_000, 0, 10_000],), "expect": 10_000},
    {
        "name": "25,000 days, peak first and low last",
        "args": (peak_first_low_last(25_000, 3),),
        "limit_ms": 500,
    },
    {"name": "25,000 falling days", "args": (falling(25_000),), "expect": 0, "limit_ms": 500},
]


def brute(prices):
    best = 0
    for i in range(len(prices)):
        for j in range(i + 1, len(prices)):
            best = max(best, prices[j] - prices[i])
    return best


def naive(prices):
    """The O(n²) shortcut the large tests must reject: for each buy day, the highest later price
    via max() on a slice. It runs in C, so it is much faster than brute()."""
    best = 0
    for i in range(len(prices)):
        best = max(best, max(prices[i:]) - prices[i])
    return best


def random_cases(rng: random.Random):
    for _ in range(300):
        yield ([rng.randint(0, 12) for _ in range(rng.randint(0, 9))],)
