"""Tests for Word Break. Expected outputs come from solution.py, checked against brute()."""

import random
from collections import deque

SHOWN = [
    {"name": "Example 1", "args": ("yellowsun", ["yell", "yellow", "sun"]), "expect": True},
    {"name": "Example 2", "args": ("applepenapple", ["apple", "pen"]), "expect": True},
    {
        "name": "Example 3",
        "args": ("catsandog", ["cats", "dog", "sand", "and", "cat"]),
        "expect": False,
    },
]

RUNS_OF_A = ["a" * k for k in range(1, 11)]  # a, aa, ..., aaaaaaaaaa
AB_WORDS = ["a", "b", "ab", "ba", "aba", "bab", "abab"]

HIDDEN = [
    {"name": "the whole string is one word", "args": ("a", ["a"]), "expect": True},
    {"name": "no word fits", "args": ("a", ["b"]), "expect": False},
    {"name": "a word longer than the string", "args": ("ab", ["abc", "b"]), "expect": False},
    {
        "name": "longest and shortest first both fail",
        "args": ("goalspecial", ["go", "goal", "goals", "special"]),
        "expect": True,
    },
    {"name": "longest word first fails", "args": ("cars", ["car", "ca", "rs"]), "expect": True},
    {"name": "3 + 4 letters", "args": ("aaaaaaa", ["aaaa", "aaa"]), "expect": True},
    {
        "name": "two routes to the same position",
        "args": ("catsanddog", ["cat", "cats", "and", "sand", "dog"]),
        "expect": True,
    },
    {"name": "a word used twice", "args": ("bb", ["a", "b", "bbb", "bbbb"]), "expect": True},
    {
        "name": "short and long words mixed",
        "args": ("abcd", ["a", "abc", "b", "cd"]),
        "expect": True,
    },
    {
        "name": "300 letters that split",
        "args": (("a" * 9 + "b") * 30, ["b"] + RUNS_OF_A[:9]),
        "expect": True,
    },
    # Every way to cut the start is tried before the dead end at the very end is found: the
    # plain recursion never finishes on these.
    {
        "name": "299 a's and a b",
        "args": ("a" * 299 + "b", RUNS_OF_A),
        "expect": False,
        "limit_ms": 500,
    },
    {
        "name": "abab... and a c",
        "args": ("ab" * 149 + "c", AB_WORDS),
        "expect": False,
        "limit_ms": 500,
    },
]


def brute(s, wordDict):
    """Breadth-first search over positions: an edge i -> j for every word s[i:j]. The string
    splits exactly when position len(s) is reachable from 0."""
    words = set(wordDict)
    seen, queue = {0}, deque([0])
    while queue:
        i = queue.popleft()
        if i == len(s):
            return True
        for j in range(i + 1, len(s) + 1):
            if j not in seen and s[i:j] in words:
                seen.add(j)
                queue.append(j)
    return False


def naive(s, wordDict):
    """The plain recursion without a memo: exponential, so the large tests must reject it."""
    words = set(wordDict)

    def can_split(i):
        if i == len(s):
            return True
        return any(s[i:j] in words and can_split(j) for j in range(i + 1, len(s) + 1))

    return can_split(0)


def random_cases(rng: random.Random):
    for _ in range(300):
        s = "".join(rng.choice("ab") for _ in range(rng.randint(1, 12)))
        vocabulary = {
            "".join(rng.choice("ab") for _ in range(rng.randint(1, 4)))
            for _ in range(rng.randint(1, 5))
        }
        yield s, sorted(vocabulary)
