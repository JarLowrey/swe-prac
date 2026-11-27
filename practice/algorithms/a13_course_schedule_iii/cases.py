"""Tests for Course Schedule III. Expected outputs come from solution.py, checked against brute()
(every subset, so the hidden tests without a time limit stay small)."""

import random

SHOWN = [
    {
        "name": "Example 1",
        "args": ([[100, 200], [200, 1300], [1000, 1250], [2000, 3200]],),
        "expect": 3,
    },
    {"name": "Example 2", "args": ([[1, 2]],), "expect": 1},
    {"name": "Example 3", "args": ([[3, 2], [4, 3]],), "expect": 0},
    {"name": "Example 4", "args": ([[1, 2], [5, 6]],), "expect": 2},
]


def crunch(n: int) -> list[list[int]]:
    """n/2 two-day courses, then n/2 one-day courses, all due on the same last day: the 1-day
    courses keep replacing 2-day ones, so the heap is large and busy."""
    half = n // 2
    return [[2, n]] * half + [[1, n]] * half


def random_courses(n: int, seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    return [[rng.randint(1, 100), rng.randint(1, 10_000)] for _ in range(n)]


HIDDEN = [
    {"name": "one course that can't fit", "args": ([[5, 4]],), "expect": 0},
    {"name": "one course that just fits", "args": ([[4, 4]],), "expect": 1},
    {"name": "same last day, any order", "args": ([[1, 10], [5, 10]],), "expect": 2},
    {"name": "only one order works", "args": ([[10, 12], [10, 30], [1, 2]],), "expect": 3},
    {"name": "listed out of order", "args": ([[1, 20], [10, 11], [5, 15]],), "expect": 3},
    {"name": "sorting by duration fails", "args": ([[2, 2], [1, 10]],), "expect": 2},
    {
        "name": "drop a long course for two short ones",
        "args": ([[10, 10], [2, 11], [2, 11]],),
        "expect": 2,
    },
    {"name": "a swap", "args": ([[5, 5], [4, 6], [2, 6]],), "expect": 2},
    {"name": "equal last days", "args": ([[2, 4], [1, 4], [3, 4]],), "expect": 2},
    {"name": "identical courses", "args": ([[3, 5], [3, 5], [3, 5], [3, 5]],), "expect": 1},
    {"name": "none can be taken", "args": ([[5, 1], [3, 2], [4, 3]],), "expect": 0},
    {
        "name": "seven courses",
        "args": ([[7, 17], [3, 12], [10, 20], [9, 10], [5, 20], [10, 19], [4, 18]],),
    },
    {"name": "9,000 courses due on one day", "args": (crunch(9_000),), "limit_ms": 500},
    {"name": "8,000 random courses", "args": (random_courses(8_000, 13),), "limit_ms": 500},
]


def brute(courses):
    """Try every subset, taking each in lastDay order (a set can be taken on time exactly when
    it works in that order)."""
    n = len(courses)
    best = 0
    for mask in range(1 << n):
        chosen = sorted((courses[i] for i in range(n) if mask >> i & 1), key=lambda c: c[1])
        day, on_time = 0, True
        for duration, last_day in chosen:
            day += duration
            if day > last_day:
                on_time = False
                break
        if on_time:
            best = max(best, len(chosen))
    return best


def naive(courses):
    """Knapsack over days in lastDay order: most[t] = the most courses that can finish exactly on
    day t. O(n · D) for the largest last day D, which the large tests must reject."""
    most = {0: 0}
    for duration, last_day in sorted(courses, key=lambda c: c[1]):
        for t, count in list(most.items()):
            end = t + duration
            if end <= last_day and most.get(end, -1) < count + 1:
                most[end] = count + 1
    return max(most.values())


def random_cases(rng: random.Random):
    for _ in range(300):
        n = rng.randint(1, 9)
        yield ([[rng.randint(1, 6), rng.randint(1, 20)] for _ in range(n)],)
