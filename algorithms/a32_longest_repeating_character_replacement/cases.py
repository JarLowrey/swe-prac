"""Tests for Longest Repeating Character Replacement."""

import random
import string
from collections import Counter

SHOWN = [
    {"name": "Example 1", "args": ("ABAB", 2), "expect": 4},
    {"name": "Example 2", "args": ("EEBAA", 1), "expect": 3},
    {"name": "Example 3", "args": ("EEBEE", 1), "expect": 5},
]


def rich_tail(n: int, tail: int, k: int, seed: int) -> tuple[str, int]:
    """Random letters, then a tail where half the letters are Q: the best window is in the tail.
    With a large k every start of the brute force runs about a thousand letters."""
    rng = random.Random(seed)
    head = [rng.choice(string.ascii_uppercase) for _ in range(n - tail)]
    end = ["Q" if rng.random() < 0.5 else rng.choice(string.ascii_uppercase) for _ in range(tail)]
    return "".join(head + end), k


def two_letters(n: int, k: int, seed: int) -> tuple[str, int]:
    rng = random.Random(seed)
    return "".join(rng.choice("AB") for _ in range(n)), k


HIDDEN = [
    {"name": "one letter", "args": ("A", 0), "expect": 1},
    {"name": "no changes allowed", "args": ("AABBBCC", 0), "expect": 3},
    {"name": "k covers the whole string", "args": ("ABCDE", 5), "expect": 5},
    {"name": "k is one less than the length", "args": ("ABCD", 3), "expect": 4},
    {"name": "all the same letter", "args": ("AAAA", 2), "expect": 4},
    {"name": "answer at the end", "args": ("ABCDEFFFFF", 1), "expect": 6},
    {"name": "answer at the start", "args": ("BBBBACDEFG", 2), "expect": 6},
    {"name": "top count from an old window", "args": ("AAAABCDE", 1), "expect": 5},
    {"name": "alternating letters", "args": ("ABABABAB", 3), "expect": 7},
    {"name": "longer example", "args": ("AABABBA", 1), "expect": 4},
    {"name": "best letter changes", "args": ("AAABBBBBA", 2), "expect": 7},
    {
        "name": "12,000 letters, best window at the end",
        "args": rich_tail(12_000, 2_500, 1_000, seed=32),
        "limit_ms": 500,
    },
    {
        "name": "12,000 letters of A and B",
        "args": two_letters(12_000, 2_500, seed=320),
        "limit_ms": 500,
    },
]


def brute(s, k):
    """Every substring: length - top count <= k."""
    best = 0
    for i in range(len(s)):
        for j in range(i, len(s)):
            window = s[i : j + 1]
            if len(window) - max(Counter(window).values()) <= k:
                best = max(best, len(window))
    return best


def naive(s, k):
    """The plausible O(n²) approach: from each start, extend while the window still fits."""
    best = 0
    for i in range(len(s)):
        count: Counter = Counter()
        top = 0
        for j in range(i, len(s)):
            count[s[j]] += 1
            top = max(top, count[s[j]])
            if j - i + 1 - top > k:
                break
            best = max(best, j - i + 1)
    return best


def random_cases(rng: random.Random):
    for _ in range(400):
        alphabet = rng.choice(["AB", "ABC", "ABCDE"])
        s = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 12)))
        yield (s, rng.randint(0, len(s)))
