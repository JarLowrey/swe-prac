"""Tests for Minimum Window Substring. Every case has a unique shortest window (or none), as the
statement promises, so the comparison is exact."""

import random
import string
from collections import Counter

SHOWN = [
    {"name": "Example 1", "args": ("aebc", "abc"), "expect": "aebc"},
    {"name": "Example 2", "args": ("aetbxab", "ab"), "expect": "ab"},
    {"name": "Example 3", "args": ("acbbaca", "aba"), "expect": "baca"},
    {"name": "Example 4", "args": ("a", "aa"), "expect": ""},
]


def shortest_windows(s: str, t: str) -> list[int]:
    """Start of every shortest window: for each end, the latest start that still covers t.
    Used to keep only inputs whose answer is unique."""
    need, missing, left, found = Counter(t), len(t), 0, []
    for right, c in enumerate(s):
        missing -= need[c] > 0
        need[c] -= 1
        if missing == 0:
            while need[s[left]] < 0:  # a spare copy, or a character t doesn't need
                need[s[left]] += 1
                left += 1
            found.append((right - left + 1, left))
    if not found:
        return []
    best = min(length for length, _ in found)
    return [start for length, start in found if length == best]


def rare_letter(n: int, m: int, rare: int, seed: int) -> tuple[str, str]:
    """n random letters, and a t of m letters that includes a "Z". s holds only `rare` Z's, so
    from most starts the O(n²) scan has to run on to the next Z, thousands of letters away.
    Retries until the shortest window is unique."""
    rng = random.Random(seed)
    letters = string.ascii_letters.replace("Z", "")
    while True:
        chars = [rng.choice(letters) for _ in range(n)]
        for i in rng.sample(range(n), rare):
            chars[i] = "Z"
        s = "".join(chars)
        t = "Z" + "".join(rng.choice(letters) for _ in range(m - 1))
        if len(shortest_windows(s, t)) == 1:
            return s, t


HIDDEN = [
    {"name": "t longer than s", "args": ("ab", "abc"), "expect": ""},
    {"name": "one character, a match", "args": ("a", "a"), "expect": "a"},
    {"name": "character missing from s", "args": ("xyz", "a"), "expect": ""},
    {"name": "case matters", "args": ("aBcAb", "Ab"), "expect": "Ab"},
    {"name": "t equals s", "args": ("abc", "abc"), "expect": "abc"},
    {"name": "t is s rearranged", "args": ("cba", "abc"), "expect": "cba"},
    {"name": "answer at the start", "args": ("bcaxxxxbxxcxxa", "abc"), "expect": "bca"},
    {"name": "answer at the end", "args": ("axxbxxcxxxcab", "abc"), "expect": "cab"},
    {"name": "duplicate in t", "args": ("baxa", "aa"), "expect": "axa"},
    {"name": "three of one letter", "args": ("aaflslflsldkalskaaa", "aaa"), "expect": "aaa"},
    {"name": "every character needed", "args": ("aabbcc", "abcabc"), "expect": "aabbcc"},
    {"name": "longer example", "args": ("cabwefgewcwaefgcf", "cae"), "expect": "cwae"},
    {
        "name": "12,000 characters, window at the end",
        "args": ("a" * 11_998 + "bc", "abc"),
        "expect": "abc",
        "limit_ms": 500,
    },
    {
        "name": "15,000 random letters, one needed letter is rare",
        "args": rare_letter(15_000, 40, rare=6, seed=30),
        "limit_ms": 500,
    },
]


def brute(s, t):
    """Every window, checked by counting: the first shortest one that covers t."""
    need = Counter(t)
    best = ""
    for i in range(len(s)):
        for j in range(i, len(s)):
            window = s[i : j + 1]
            if not need - Counter(window) and (not best or len(window) < len(best)):
                best = window
    return best


def naive(s, t):
    """The plausible O(n²) approach: from each start, count forwards until the window covers t."""
    need = Counter(t)
    best = ""
    for i in range(len(s)):
        have: Counter = Counter()
        missing = len(t)
        for j in range(i, len(s)):
            c = s[j]
            have[c] += 1
            if have[c] <= need[c]:
                missing -= 1
            if missing == 0:
                if not best or j - i + 1 < len(best):
                    best = s[i : j + 1]
                break
    return best


def random_cases(rng: random.Random):
    made = 0
    while made < 300:
        alphabet = rng.choice(["ab", "abc", "abcd", "aAbB"])
        s = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 10)))
        t = "".join(rng.choice(alphabet + "z") for _ in range(rng.randint(1, 4)))
        if len(shortest_windows(s, t)) <= 1:  # unique answer, or none
            made += 1
            yield (s, t)
