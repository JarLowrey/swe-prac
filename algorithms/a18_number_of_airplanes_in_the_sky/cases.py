"""Tests for Number of Airplanes in the Sky. Expected outputs come from solution.py, checked
against brute()."""

import random

SHOWN = [
    {"name": "Example 1", "args": ([[1, 10], [2, 3], [5, 8], [4, 7]],), "expect": 3},
    {"name": "Example 2", "args": ([[1, 2], [2, 3], [3, 4]],), "expect": 1},
    {"name": "Example 3", "args": ([[1, 2], [1, 4]],), "expect": 2},
]


def random_flights(n: int, seed: int) -> list[list[int]]:
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        takeoff = rng.randint(0, 4_950)
        out.append([takeoff, takeoff + rng.randint(1, 50)])
    return out


def all_airborne(n: int) -> list[list[int]]:
    """Plane i takes off at time i and every plane lands at 9,999, so all n are in the air at
    time n - 1; listed in a scrambled order."""
    out = [[i, 9_999] for i in range(n)]
    random.Random(18).shuffle(out)
    return out


HIDDEN = [
    {"name": "no planes", "args": ([],), "expect": 0},
    {"name": "one plane", "args": ([[3, 7]],), "expect": 1},
    {
        "name": "three land as three take off",
        "args": ([[1, 5], [2, 5], [3, 5], [5, 8], [5, 9], [5, 10]],),
        "expect": 3,
    },
    {"name": "identical flights", "args": ([[2, 6], [2, 6], [2, 6], [2, 6]],), "expect": 4},
    {"name": "nested flights", "args": ([[1, 10], [2, 5], [3, 4]],), "expect": 3},
    {"name": "goes up and down", "args": ([[1, 10], [2, 3], [5, 6]],), "expect": 2},
    {"name": "same takeoff, different landings", "args": ([[1, 2], [1, 3], [1, 4]],), "expect": 3},
    {"name": "unsorted input", "args": ([[7, 9], [1, 3], [2, 8], [4, 5]],)},
    {
        "name": "ties mixed with overlaps",
        "args": ([[1, 4], [4, 6], [2, 4], [4, 5], [3, 7]],),
        "expect": 3,
    },
    {
        "name": "times up to a billion",
        "args": ([[0, 10**9], [5 * 10**8, 10**9], [10**9 - 1, 10**9]],),
    },
    {"name": "a relay of 50 flights", "args": ([[i, i + 1] for i in range(50)],), "expect": 1},
    {
        "name": "busiest at the end",
        "args": ([[1, 2], [3, 4], [5, 6], [10, 20], [11, 20], [12, 20], [13, 20]],),
    },
    {"name": "7,000 random flights", "args": (random_flights(7_000, 1),), "limit_ms": 500},
    {"name": "7,000 flights in the air at once", "args": (all_airborne(7_000),), "limit_ms": 500},
]


def brute(airplanes):
    """The count only rises at a takeoff, so the busiest moment is a takeoff time: count the
    planes flying at each one. O(n²): also the too-slow approach the large tests reject."""
    best = 0
    for t, _ in airplanes:
        best = max(best, sum(1 for takeoff, landing in airplanes if takeoff <= t < landing))
    return best


def random_cases(rng: random.Random):
    for _ in range(300):
        flights = []
        for _ in range(rng.randint(0, 9)):
            takeoff = rng.randint(0, 10)
            flights.append([takeoff, takeoff + rng.randint(1, 6)])
        yield (flights,)
