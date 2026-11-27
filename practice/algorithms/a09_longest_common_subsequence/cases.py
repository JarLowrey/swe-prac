"""Tests for Longest Common Subsequence. Expected outputs come from solution.py, checked against
brute()."""

import random
from itertools import combinations

SHOWN = [
    {"name": "Example 1", "args": ("abcde", "ace"), "expect": 3},
    {"name": "Example 2", "args": ("abc", "abc"), "expect": 3},
    {"name": "Example 3", "args": ("abc", "def"), "expect": 0},
]


def random_text(seed: int, n: int, letters: str) -> str:
    rng = random.Random(seed)
    return "".join(rng.choice(letters) for _ in range(n))


HIDDEN = [
    {"name": "one matching letter", "args": ("a", "a"), "expect": 1},
    {"name": "one letter each, different", "args": ("a", "b"), "expect": 0},
    {"name": "a single shared letter in the middle", "args": ("ace", "cbd"), "expect": 1},
    {"name": "only the last letter is shared", "args": ("ace", "def"), "expect": 1},
    {"name": "the first match is a trap", "args": ("zabcd", "abcdz"), "expect": 4},
    {"name": "reversed", "args": ("abcd", "dcba"), "expect": 1},
    {"name": "repeated letters", "args": ("aaaa", "aa"), "expect": 2},
    {"name": "few matches", "args": ("bsbininm", "jmjkbkjkv"), "expect": 1},
    {"name": "almost contained", "args": ("abcba", "abcbcba"), "expect": 5},
    {"name": "scattered matches", "args": ("oxcpqrsvwf", "shmtulqrypy"), "expect": 2},
    {
        "name": "one long, one short",
        "args": ("thequickbrownfoxjumpsoverthelazydog", "fox"),
        "expect": 3,
    },
    # Plain recursion branches on every mismatch: these never finish without a memo. 300 x 300
    # keeps a memoized top-down solution well inside the limit, even on a busy machine.
    {
        "name": "300 x 300 random letters",
        "args": (random_text(9, 300, "abcd"), random_text(99, 300, "abcd")),
        "limit_ms": 500,
    },
    {
        "name": "300 x 300, nothing in common",
        "args": ("ab" * 150, "cd" * 150),
        "expect": 0,
        "limit_ms": 500,
    },
]


def is_subsequence(small, big):
    letters = iter(big)
    return all(ch in letters for ch in small)  # `in` consumes the iterator up to the match


def brute(text1, text2):
    """Try the shorter string's subsequences from the longest down (small inputs only)."""
    short, long = sorted((text1, text2), key=len)
    for size in range(len(short), 0, -1):
        for chosen in combinations(short, size):
            if is_subsequence(chosen, long):
                return size
    return 0


def naive(text1, text2):
    """The plain recursion without a memo: exponential, so the large tests must reject it."""

    def lcs(i, j):
        if i == len(text1) or j == len(text2):
            return 0
        if text1[i] == text2[j]:
            return 1 + lcs(i + 1, j + 1)
        return max(lcs(i + 1, j), lcs(i, j + 1))

    return lcs(0, 0)


def random_cases(rng: random.Random):
    for _ in range(300):
        yield (
            "".join(rng.choice("abc") for _ in range(rng.randint(1, 9))),
            "".join(rng.choice("abc") for _ in range(rng.randint(1, 9))),
        )
