"""Tests for Longest Palindromic Substring. Several answers can be right ("bab" or "aba"), so
checker.py accepts any palindromic substring as long as the reference's answer."""

import random
import string

SHOWN = [
    {"name": "Example 1", "args": ("baba",), "expect": "bab"},
    {"name": "Example 2", "args": ("babab",), "expect": "babab"},
    {"name": "Example 3", "args": ("cbbd",), "expect": "bb"},
]


def planted(n: int, length: int, seed: int, at_end: bool) -> str:
    """n random lowercase letters with a palindrome of the given length at one end. Random text
    has only short palindromes, so the planted one is the answer. Checking every substring takes
    seconds; expanding around centers stops after a step or two almost everywhere."""
    rng = random.Random(seed)
    half = "".join(rng.choice(string.ascii_lowercase) for _ in range(length // 2))
    middle = rng.choice(string.ascii_lowercase) if length % 2 else ""
    palindrome = half + middle + half[::-1]
    rest = "".join(rng.choice(string.ascii_lowercase) for _ in range(n - length))
    return rest + palindrome if at_end else palindrome + rest


HIDDEN = [
    {"name": "one character", "args": ("a",)},
    {"name": "two different characters", "args": ("ab",)},
    {"name": "two equal characters", "args": ("zz",)},
    {"name": "no palindrome longer than one", "args": ("abcdefg",)},
    {"name": "whole string, even length", "args": ("abccba",)},
    {"name": "answer at the start", "args": ("racecarxyz",)},
    {"name": "answer at the end", "args": ("xyzabcdcba",)},
    {"name": "reversed common substring is not a palindrome", "args": ("abacdfgdcaba",)},
    {"name": "even palindrome inside", "args": ("forgeeksskeegfor",)},
    {"name": "case matters", "args": ("Abcba",)},
    {"name": "digits", "args": ("9123214",)},
    {"name": "overlapping palindromes", "args": ("abababa",)},
    {"name": "1,000 copies of one letter", "args": ("a" * 1000,)},
    {
        "name": "2,500 letters, palindrome at the end",
        "args": (planted(2500, 41, seed=26, at_end=True),),
        "limit_ms": 500,
    },
    {
        "name": "2,500 letters, even palindrome at the start",
        "args": (planted(2500, 40, seed=262, at_end=False),),
        "limit_ms": 500,
    },
]


def brute(s):
    """Every substring, longest palindrome kept: O(n³). It is also the slow approach the
    2,500-letter tests reject (both O(n²) solutions pass them)."""
    best = ""
    for i in range(len(s)):
        for j in range(i, len(s)):
            sub = s[i : j + 1]
            if sub == sub[::-1] and len(sub) > len(best):
                best = sub
    return best


def random_cases(rng: random.Random):
    for _ in range(400):
        alphabet = rng.choice(["ab", "abc", "aB1", "xyz"])
        yield ("".join(rng.choice(alphabet) for _ in range(rng.randint(1, 12))),)
