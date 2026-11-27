"""Tests for Koko Eating Bananas. Expected outputs come from solution.py, checked against brute(),
which tries every speed from 1 upwards. brute() is also the slow approach the time-limited tests
must reject, so every test without a limit keeps the answer small enough for it."""

import random

SHOWN = [
    {"name": "Example 1", "args": ([3, 5, 11], 6), "expect": 4},
    {"name": "Example 2", "args": ([1, 2, 3, 100], 4), "expect": 100},
    {"name": "Example 3", "args": ([3, 6], 100), "expect": 1},
]


def one_hour_per_pile(n: int, seed: int) -> tuple[list[int], int]:
    """n piles of up to a billion bananas and h = n: the answer is the largest pile, which trying
    speeds from 1 upwards reaches only after about a billion checks."""
    rng = random.Random(seed)
    return [rng.randint(1, 10**9) for _ in range(n)], n


def one_huge_pile(n: int, seed: int) -> tuple[list[int], int]:
    """A pile of a billion among n - 1 piles of at most 9, and two hours for the big pile: the
    answer is 500 million, far above the average-rate bound sum(piles) / h (about 200,000)."""
    rng = random.Random(seed)
    piles = [rng.randint(1, 9) for _ in range(n - 1)]
    piles.insert(rng.randrange(n), 10**9)
    return piles, n + 1


HIDDEN = [
    {"name": "one pile, one hour", "args": ([7], 1), "expect": 7},
    {"name": "one pile, several hours", "args": ([30], 7), "expect": 5},
    {"name": "finishes in exactly h hours", "args": ([3, 6, 7, 11], 8), "expect": 4},
    {"name": "one hour per pile", "args": ([30, 11, 23, 4, 20], 5), "expect": 30},
    {"name": "one spare hour", "args": ([30, 11, 23, 4, 20], 6), "expect": 23},
    {"name": "all piles equal", "args": ([5, 5, 5, 5], 8), "expect": 3},
    {"name": "piles of one banana", "args": ([1, 1, 1, 1], 4), "expect": 1},
    {"name": "h equals the number of bananas", "args": ([2, 9, 4], 15), "expect": 1},
    {"name": "one hour short of speed 1", "args": ([2, 9, 4], 14), "expect": 2},
    {"name": "the answer isn't a pile size", "args": ([9, 8, 7], 6), "expect": 5},
    {"name": "a billion bananas, a billion hours", "args": ([10**9], 10**9), "expect": 1},
    {"name": "large piles, rounding up matters", "args": ([10**9] * 3, 10**9), "expect": 4},
    {
        "name": "1,000 huge piles, one hour each",
        "args": one_hour_per_pile(1000, 45),
        "limit_ms": 500,
    },
    {"name": "one huge pile among 5,000", "args": one_huge_pile(5000, 46), "limit_ms": 500},
]


def hours(piles, k):
    return sum((p + k - 1) // k for p in piles)


def brute(piles, h):
    """Try every speed from 1 upwards; the first that fits is the answer."""
    k = 1
    while hours(piles, k) > h:
        k += 1
    return k


def random_cases(rng: random.Random):
    for _ in range(300):
        piles = [rng.randint(1, 30) for _ in range(rng.randint(1, 7))]
        # From one hour per pile (the answer is the largest pile) up to more than enough hours.
        h = rng.choice([len(piles), rng.randint(len(piles), sum(piles) + 3)])
        yield (piles, h)
