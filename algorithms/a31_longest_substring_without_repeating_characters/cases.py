"""Tests for Longest Substring Without Repeating Characters."""

import random

SHOWN = [
    {"name": "Example 1", "args": ("abcda",), "expect": 4},
    {"name": "Example 2", "args": ("bbbb",), "expect": 1},
    {"name": "Example 3", "args": ("pwwkew",), "expect": 3},
]

PRINTABLE = "".join(chr(c) for c in range(32, 127))  # the 95 printable ASCII characters
CYCLE = PRINTABLE[:-1]  # 94 of them, without "~"


def cycled(n: int) -> str:
    """The 94-character cycle repeated to length n: every run of 94 is all different."""
    return (CYCLE * (n // len(CYCLE) + 1))[:n]


HIDDEN = [
    {"name": "empty string", "args": ("",), "expect": 0},
    {"name": "one character", "args": ("a",), "expect": 1},
    {"name": "a space", "args": (" ",), "expect": 1},
    {"name": "two different characters", "args": ("au",), "expect": 2},
    {"name": "start must not move back", "args": ("abba",), "expect": 2},
    {"name": "restart after the earlier copy", "args": ("dvdf",), "expect": 3},
    {"name": "repeat from before the window", "args": ("tmmzuxt",), "expect": 5},
    {"name": "answer at the start", "args": ("abcdeaaaa",), "expect": 5},
    {"name": "answer at the end", "args": ("aaaaabcde",), "expect": 5},
    {"name": "symbols and spaces", "args": ("hi, you! hi?",)},
    {"name": "case matters", "args": ("aAbBa",), "expect": 4},
    {"name": "all 95 printable characters", "args": (PRINTABLE,), "expect": 95},
    {
        # Windows of 94 characters everywhere; the "~" at the very end makes one of 95.
        "name": "20,000 characters, longest at the end",
        "args": (cycled(19_999) + "~",),
        "expect": 95,
        "limit_ms": 500,
    },
    {
        "name": "20,000 characters, longest in the middle",
        "args": (cycled(10_000) + "~" + cycled(9_999),),
        "expect": 95,
        "limit_ms": 500,
    },
]


def brute(s):
    """Every substring, checked with a set: O(n³)."""
    best = 0
    for i in range(len(s)):
        for j in range(i, len(s)):
            if len(set(s[i : j + 1])) == j - i + 1:
                best = max(best, j - i + 1)
    return best


def naive(s):
    """Check substrings from each start, rebuilding the set each time, until one repeats:
    O(n·σ²) for an alphabet of σ characters. Growing one set per start instead is O(n·σ), which
    is fast enough here because σ <= 95; the window is O(n) whatever the alphabet."""
    best = 0
    for i in range(len(s)):
        for j in range(i, len(s)):
            if len(set(s[i : j + 1])) < j - i + 1:
                break  # every longer substring from i repeats too
            best = max(best, j - i + 1)
    return best


def random_cases(rng: random.Random):
    for _ in range(400):
        alphabet = rng.choice(["ab", "abc", "abcde", "a b!", "aAbB1"])
        yield ("".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12))),)
