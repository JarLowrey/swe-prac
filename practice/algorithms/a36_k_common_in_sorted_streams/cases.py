"""Tests for Values in K Sorted Streams. Expected outputs come from solution.py, checked against
brute(). There is no time-limited test: counting with sets is fast too; what it costs is the
memory to hold every value, which a test can't measure."""

import random

SHOWN = [
    {
        "name": "Example 1",
        "args": ([[1, 2, 3, 20], [-5, -2, 0, 3], [20, 40, 50, 80]], 2),
        "expect": [3, 20],
    },
    {"name": "Example 2", "args": ([[1, 2, 3], [4, 4, 4], [5, 6]], 2), "expect": []},
    {"name": "Example 3", "args": ([[5, 6], [4, 5, 20], [20]], 2), "expect": [5, 20]},
]


def many_streams(x: int, seed: int) -> list[list[int]]:
    """x streams of up to 40 sorted values, with repeats inside streams."""
    rng = random.Random(seed)
    return [sorted(rng.randint(0, 300) for _ in range(rng.randint(0, 40))) for _ in range(x)]


HIDDEN = [
    {"name": "no streams", "args": ([], 1), "expect": []},
    {"name": "only empty streams", "args": ([[], [], []], 1), "expect": []},
    {"name": "k larger than the number of streams", "args": ([[1, 2], [1, 2]], 3), "expect": []},
    {
        "name": "k = 1: every distinct value",
        "args": ([[5, 6], [4, 5, 20], [20]], 1),
        "expect": [4, 5, 6, 20],
    },
    {
        "name": "in every stream",
        "args": ([[1, 2, 3, 4], [2, 3, 4, 5], [0, 2, 4, 6]], 3),
        "expect": [2, 4],
    },
    {"name": "empty streams mixed in", "args": ([[], [1, 1, 2], [], [2]], 2), "expect": [2]},
    {"name": "repeats in every stream", "args": ([[7, 7, 7], [7, 7], [7]], 3), "expect": [7]},
    {"name": "one stream with repeats", "args": ([[1, 1, 2, 3, 3]], 1), "expect": [1, 2, 3]},
    {"name": "negative values", "args": ([[-3, -1, 0], [-3, 0, 2], [-2, 0]], 2), "expect": [-3, 0]},
    {
        "name": "the common value comes last",
        "args": ([[1, 2, 3, 100], [4, 5, 6, 100], [7, 100]], 3),
        "expect": [100],
    },
    {
        "name": "one long stream, short ones",
        "args": ([list(range(100)), [5], [50], [99], [5, 50]], 2),
    },
    {
        "name": "identical streams",
        "args": ([[1, 2, 3], [1, 2, 3], [1, 2, 3], [1, 2, 3]], 4),
        "expect": [1, 2, 3],
    },
    {"name": "values up to a billion", "args": ([[-(10**9), 0, 10**9], [10**9], [-(10**9)]], 2)},
    {"name": "300 streams", "args": (many_streams(300, 36), 25)},
]


def brute(streams, k):
    """Count, for each value, the streams that contain it (a set per stream)."""
    counts: dict[int, int] = {}
    for stream in streams:
        for value in set(stream):
            counts[value] = counts.get(value, 0) + 1
    return sorted(value for value, c in counts.items() if c >= k)


def random_cases(rng: random.Random):
    for _ in range(400):
        x = rng.randint(0, 5)
        streams = [sorted(rng.randint(-4, 4) for _ in range(rng.randint(0, 6))) for _ in range(x)]
        yield (streams, rng.randint(1, x + 1))
