"""Tests for 3Sum. The triplets may come back in any order, and so may the values inside each one
("compare": "unordered_nested"). Expected outputs come from solution.py, checked against brute()."""

import random

SHOWN = [
    {"name": "Example 1", "args": ([-1, 0, 1, 2, -1, -4],), "expect": [[-1, -1, 2], [-1, 0, 1]]},
    {"name": "Example 2", "args": ([-3, -3, 1, 2],), "expect": [[-3, 1, 2]]},
    {"name": "Example 3", "args": ([0, 1, 1],), "expect": []},
]


def wide_random(n: int, seed: int) -> list[int]:
    """n distinct values spread over the whole range: a few hundred triplets among n³/6 triples,
    so checking every triple is far too slow."""
    return random.Random(seed).sample(range(-(10**5), 10**5 + 1), n)


def many_repeats(n: int, seed: int) -> list[int]:
    """n values from -6 to 6: every triplet can be made in many ways, so the repeats must be
    skipped, and checking every triple is too slow."""
    rng = random.Random(seed)
    return [rng.randint(-6, 6) for _ in range(n)]


HIDDEN = [
    {"name": "empty array", "args": ([],), "expect": []},
    {"name": "two numbers", "args": ([1, -1],), "expect": []},
    {"name": "three zeros", "args": ([0, 0, 0],), "expect": [[0, 0, 0]]},
    {"name": "five zeros", "args": ([0, 0, 0, 0, 0],), "expect": [[0, 0, 0]]},
    {"name": "all positive", "args": ([1, 2, 3, 4],), "expect": []},
    {"name": "all negative", "args": ([-5, -2, -1],), "expect": []},
    {"name": "both copies of a value", "args": ([-3, -3, 6],), "expect": [[-3, -3, 6]]},
    {"name": "both copies, in another order", "args": ([2, -1, -1],), "expect": [[-1, -1, 2]]},
    {"name": "repeats inside the pair", "args": ([-2, 0, 0, 2, 2],), "expect": [[-2, 0, 2]]},
    {"name": "a value and its negative", "args": ([-5, 0, 5, 5, -5],), "expect": [[-5, 0, 5]]},
    {"name": "many triplets", "args": ([-4, -2, -2, -2, 0, 1, 2, 2, 2, 3, 3, 4, 4, 6, 6],)},
    {
        "name": "largest values",
        "args": ([100_000, -100_000, 0, 50_000, -50_000],),
        "expect": [[-100_000, 0, 100_000], [-50_000, 0, 50_000]],
    },
    {"name": "600 distinct values", "args": (wide_random(600, 5),), "limit_ms": 500},
    {"name": "600 values from -6 to 6", "args": (many_repeats(600, 6),), "limit_ms": 500},
]


def brute(nums):
    """Every triple, each triplet sorted so repeats collapse in the set. Also the O(n³) approach
    the large tests must reject."""
    found = set()
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                if nums[i] + nums[j] + nums[k] == 0:
                    found.add(tuple(sorted((nums[i], nums[j], nums[k]))))
    return [list(t) for t in found]


def random_cases(rng: random.Random):
    for _ in range(300):
        yield ([rng.randint(-5, 5) for _ in range(rng.randint(0, 10))],)
