"""Tests for Merge k Sorted Lists. Lists are written as plain values: the runner builds the linked
lists ("listnodes") and reads the returned list back ("result": "listnode")."""

import random

SHOWN = [
    {
        "name": "Example 1",
        "args": ([[1, 4, 5], [1, 3, 4], [2, 6]],),
        "expect": [1, 1, 2, 3, 4, 4, 5, 6],
    },
    {"name": "Example 2", "args": ([],), "expect": []},
    {"name": "Example 3", "args": ([[]],), "expect": []},
]


def single_nodes(k: int, seed: int) -> list[list[int]]:
    """k one-node lists holding 0..k-1 in a scrambled order: the most lists the constraints
    allow, which is what makes scanning every head (or merging one list at a time) slow."""
    values = list(range(k))
    random.Random(seed).shuffle(values)
    return [[v] for v in values]


def interleaved(k: int, length: int) -> list[list[int]]:
    """List i is i, i + k, i + 2k, ...: every list's values interleave with every other's."""
    return [[i + k * j for j in range(length)] for i in range(k)]


HIDDEN = [
    {"name": "only empty lists", "args": ([[], [], []],), "expect": []},
    {"name": "one list", "args": ([[1, 2, 3]],), "expect": [1, 2, 3]},
    {"name": "empty lists mixed in", "args": ([[], [1], [], [0, 2]],), "expect": [0, 1, 2]},
    {
        "name": "equal values in every list",
        "args": ([[1, 1], [1, 1], [1]],),
        "expect": [1, 1, 1, 1, 1],
    },
    {
        "name": "nine nodes with duplicates",
        "args": ([[1, 2, 3], [2, 3, 4], [5, 6, 7]],),
        "expect": [1, 2, 2, 3, 3, 4, 5, 6, 7],
    },
    {"name": "negative values", "args": ([[-10, -5, 0], [-7, 3], [-8]],)},
    {"name": "very different lengths", "args": ([[5], list(range(0, 40, 2)), [3, 7]],)},
    {"name": "two interleaved lists", "args": ([[1, 3, 5, 7, 9], [2, 4, 6, 8, 10]],)},
    {"name": "single nodes in reverse order", "args": ([[5], [4], [3], [2], [1]],)},
    {"name": "all nodes in one list", "args": ([[], [], [1, 2, 3], []],)},
    {"name": "lists that don't interleave", "args": ([[1, 2], [10, 11], [5, 6]],)},
    {"name": "10,000 one-node lists", "args": (single_nodes(10_000, 42),), "limit_ms": 500},
    {"name": "2,000 lists of 5 nodes", "args": (interleaved(2_000, 5),), "limit_ms": 500},
]


def brute(lists):
    return sorted(v for values in lists for v in values)


def naive(lists):
    """Scan every list's head for the smallest, k comparisons per output value: O(N·k). The
    large tests must reject it."""
    heads = [0] * len(lists)
    out = []
    while True:
        best = -1
        for i, values in enumerate(lists):
            if heads[i] < len(values) and (best < 0 or values[heads[i]] < lists[best][heads[best]]):
                best = i
        if best < 0:
            return out
        out.append(lists[best][heads[best]])
        heads[best] += 1


def random_cases(rng: random.Random):
    for _ in range(300):
        k = rng.randint(0, 6)
        yield ([sorted(rng.randint(-5, 5) for _ in range(rng.randint(0, 5))) for _ in range(k)],)
