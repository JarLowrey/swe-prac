"""Tests for Valid Anagram. Expected outputs come from solution.py, checked against brute()."""

import random
import string

SHOWN = [
    {"name": "Example 1", "args": ("anagram", "nagaram"), "expect": True},
    {"name": "Example 2", "args": ("rat", "car"), "expect": False},
    {"name": "Example 3", "args": ("tea", "eat"), "expect": True},
]


def letters(n: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    return [rng.choice(string.ascii_lowercase) for _ in range(n)]


def sorted_and_reversed(n: int, seed: int) -> tuple[str, str]:
    """s in a-to-z order and t in z-to-a order: crossing off s's letters in t searches past
    almost all of t for every letter."""
    chars = letters(n, seed)
    return "".join(sorted(chars)), "".join(sorted(chars, reverse=True))


def one_z_short(n: int, seed: int) -> tuple[str, str]:
    """Like sorted_and_reversed, but t trades one z for an a. s's z's come last, so crossing
    letters off only fails at the very end."""
    s, t = sorted_and_reversed(n, seed)
    assert t[0] == "z"
    return s, t[1:] + "a"


HIDDEN = [
    {"name": "two empty strings", "args": ("", ""), "expect": True},
    {"name": "one empty string", "args": ("a", ""), "expect": False},
    {"name": "different lengths, same letters", "args": ("ab", "aab"), "expect": False},
    {"name": "same letters, different counts", "args": ("aab", "abb"), "expect": False},
    {"name": "identical strings", "args": ("abc", "abc"), "expect": True},
    {"name": "one letter, the same", "args": ("a", "a"), "expect": True},
    {"name": "one letter, different", "args": ("a", "b"), "expect": False},
    {"name": "one letter repeated", "args": ("aaaa", "aaaa"), "expect": True},
    {"name": "the last letter differs", "args": ("aaaa", "aaab"), "expect": False},
    {"name": "listen and silent", "args": ("listen", "silent"), "expect": True},
    {
        "name": "the whole alphabet, reversed",
        "args": (string.ascii_lowercase, string.ascii_lowercase[::-1]),
        "expect": True,
    },
    {"name": "t is s with one letter changed", "args": ("anagram", "anagrem"), "expect": False},
    {
        "name": "30,000 letters, an anagram",
        "args": sorted_and_reversed(30_000, 28),
        "limit_ms": 500,
    },
    {"name": "30,000 letters, one z short", "args": one_z_short(30_000, 28), "limit_ms": 500},
]


def brute(s, t):
    return sorted(s) == sorted(t)


def naive(s, t):
    """The O(n²) approach the large tests must reject: cross each letter of s off a list of t's
    letters (list.remove searches from the front)."""
    if len(s) != len(t):
        return False
    rest = list(t)
    for ch in s:
        if ch not in rest:
            return False
        rest.remove(ch)
    return True


def random_cases(rng: random.Random):
    for _ in range(300):
        s = "".join(rng.choice("abc") for _ in range(rng.randint(0, 8)))
        kind = rng.random()
        if kind < 0.4:  # a true anagram
            t = "".join(rng.sample(s, len(s)))
        elif kind < 0.7 and s:  # an anagram with one letter changed
            chars = rng.sample(s, len(s))
            chars[rng.randrange(len(chars))] = rng.choice("abcd")
            t = "".join(chars)
        else:  # unrelated
            t = "".join(rng.choice("abc") for _ in range(rng.randint(0, 8)))
        yield (s, t)
