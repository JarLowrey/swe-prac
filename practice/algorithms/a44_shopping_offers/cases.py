"""Tests for Shopping Offers. Expected outputs come from solution.py, checked against brute(),
which tries every combination of offer counts (no recursion, no memo)."""

import itertools
import random

SHOWN = [
    {
        "name": "Example 1",
        "args": ([2, 5], [[3, 0, 5], [1, 2, 10]], [3, 2]),
        "expect": 14,
    },
    {
        "name": "Example 2",
        "args": ([2, 3, 4], [[1, 1, 0, 4], [2, 2, 1, 9]], [1, 2, 1]),
        "expect": 11,
    },
    {"name": "Example 3", "args": ([2, 2], [[2, 2, 0]], [1, 1]), "expect": 4},
]

# The two time-limited tests: a few hundred reachable states, so the memoized reference takes a
# few ms, while the same recursion without a memo makes 1.2 × 10^11 calls (three items, eight of
# each) and 1.3 × 10^6 calls, about 8 s (six items, four of each, eight overlapping bundles).
# Every offer is cheaper than its items at full price, so dropping poor offers doesn't help.
SIX_BUNDLES = [
    [1, 1, 0, 0, 0, 0, 2],
    [0, 0, 1, 1, 0, 0, 6],
    [0, 0, 0, 0, 1, 1, 10],
    [1, 0, 1, 0, 1, 0, 8],
    [0, 1, 0, 1, 0, 1, 11],
    [1, 1, 1, 1, 1, 1, 19],
    [2, 2, 2, 0, 0, 0, 10],
    [0, 0, 0, 2, 2, 2, 28],
]

HIDDEN = [
    {"name": "no offers", "args": ([3, 4], [], [2, 1]), "expect": 10},
    {"name": "nothing needed", "args": ([5, 5], [[1, 1, 3]], [0, 0]), "expect": 0},
    {"name": "offer dearer than full price", "args": ([1, 1], [[1, 1, 5]], [2, 2]), "expect": 4},
    {
        "name": "a bundle beats two single offers",
        "args": ([2, 2], [[1, 0, 1], [0, 1, 1], [1, 1, 1]], [1, 1]),
        "expect": 1,
    },
    {"name": "one offer used three times", "args": ([5], [[3, 10]], [10]), "expect": 35},
    {
        "name": "biggest saving first is wrong",
        "args": ([10, 10, 10], [[2, 2, 0, 20], [1, 0, 1, 5], [0, 1, 1, 5]], [2, 2, 2]),
        "expect": 30,
    },
    {
        "name": "an offer with no items",
        "args": ([4, 6], [[0, 0, 3], [1, 1, 8]], [1, 2]),
        "expect": 14,
    },
    {"name": "a free item", "args": ([0, 3], [[2, 1, 2]], [2, 1]), "expect": 2},
    {"name": "a free offer that fits", "args": ([4], [[2, 0]], [5]), "expect": 4},
    {
        "name": "fits one item but not the other",
        "args": ([1, 10], [[1, 3, 5]], [5, 2]),
        "expect": 25,
    },
    {
        "name": "six items",
        "args": (
            [2, 3, 4, 5, 6, 7],
            [
                [1, 1, 1, 0, 0, 0, 7],
                [0, 0, 0, 1, 1, 1, 15],
                [2, 0, 0, 0, 0, 2, 15],
                [1, 1, 1, 1, 1, 1, 24],
                [0, 2, 0, 2, 0, 0, 13],
            ],
            [2, 2, 3, 3, 1, 2],
        ),
        "expect": 50,
    },
    {
        "name": "three items, eight of each",
        "args": (
            [5, 6, 7],
            [[1, 0, 0, 4], [0, 1, 0, 5], [0, 0, 1, 6], [1, 1, 1, 15], [2, 1, 0, 12]],
            [8, 8, 8],
        ),
        "limit_ms": 500,
    },
    {
        "name": "six items, eight bundles",
        "args": ([1, 2, 3, 4, 5, 6], SIX_BUNDLES, [4, 4, 4, 4, 4, 4]),
        "limit_ms": 500,
    },
]


def brute(price, special, needs):
    """Try every combination of offer counts (each offer 0, 1, 2... times, up to what fits on its
    own), then buy whatever is left at full price."""
    n = len(price)
    useful = [o for o in special if any(o[:n])]  # an offer with no items never helps
    limits = [min(needs[i] // o[i] for i in range(n) if o[i]) for o in useful]
    best = sum(p * q for p, q in zip(price, needs, strict=True))
    for counts in itertools.product(*(range(c + 1) for c in limits)):
        left = [
            needs[i] - sum(c * o[i] for c, o in zip(counts, useful, strict=True)) for i in range(n)
        ]
        if min(left) < 0:
            continue
        cost = sum(c * o[n] for c, o in zip(counts, useful, strict=True))
        best = min(best, cost + sum(p * q for p, q in zip(price, left, strict=True)))
    return best


def naive(price, special, needs):
    """The plausible but too-slow approach: the same recursion with no memo, which solves the
    same remaining needs again for every order of offers that reaches them."""
    n = len(price)
    offers = [o for o in special if any(o[:n])]

    def cheapest(left):
        best = sum(p * q for p, q in zip(price, left, strict=True))
        for o in offers:
            rest = [left[i] - o[i] for i in range(n)]
            if min(rest) >= 0:
                best = min(best, o[n] + cheapest(rest))
        return best

    return cheapest(list(needs))


def random_cases(rng: random.Random):
    for _ in range(300):
        n = rng.randint(1, 3)
        price = [rng.randint(0, 6) for _ in range(n)]
        needs = [rng.randint(0, 4) for _ in range(n)]
        special = [
            [rng.randint(0, 3) for _ in range(n)] + [rng.randint(0, 15)]
            for _ in range(rng.randint(0, 4))
        ]
        yield (price, special, needs)
