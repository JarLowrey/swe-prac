"""Tests for the Reverse List fixture (lists are written as plain values)."""

import random

SHOWN = [
    {"name": "Example 1", "args": ([1, 2, 3],), "expect": [3, 2, 1]},
]

HIDDEN = [
    {"name": "secret empty", "args": ([],), "expect": []},
    {"name": "secret one node", "args": ([5],)},
    {"name": "secret two nodes", "args": ([1, 2],)},
]


def brute(values):
    return values[::-1]


def random_cases(rng: random.Random):
    for _ in range(20):
        yield ([rng.randint(0, 9) for _ in range(rng.randint(0, 8))],)
