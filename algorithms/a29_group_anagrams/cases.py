"""Tests for Group Anagrams. The groups may come back in any order, and so may the words inside
each group ("compare": "unordered_nested"). Expected outputs come from solution.py, checked against
brute()."""

import random
import string

SHOWN = [
    {
        "name": "Example 1",
        "args": (["eat", "tea", "tan", "ate", "nat", "bat"],),
        "expect": [["bat"], ["nat", "tan"], ["ate", "eat", "tea"]],
    },
    {"name": "Example 2", "args": ([""],), "expect": [[""]]},
    {"name": "Example 3", "args": (["ab", "ba", "aba"],), "expect": [["ab", "ba"], ["aba"]]},
]


def word(rng: random.Random, low: int, high: int) -> str:
    return "".join(rng.choice(string.ascii_lowercase) for _ in range(rng.randint(low, high)))


def some_groups(n: int, seed: int) -> list[str]:
    """n short words: most have no anagram in the list, some come in groups of two or three.
    With thousands of groups, scanning the groups for each word is too slow."""
    rng = random.Random(seed)
    words: list[str] = []
    while len(words) < n:
        w = word(rng, 3, 7)
        for _ in range(rng.choice((1, 1, 1, 2, 3))):
            words.append("".join(rng.sample(w, len(w))))
    words = words[:n]
    rng.shuffle(words)
    return words


def no_two_anagrams(n: int, seed: int) -> list[str]:
    """n words, no two of them anagrams: n groups of one."""
    rng = random.Random(seed)
    keys: set[str] = set()
    words: list[str] = []
    while len(words) < n:
        w = word(rng, 2, 6)
        key = "".join(sorted(w))
        if key not in keys:
            keys.add(key)
            words.append(w)
    return words


def long_words() -> list[str]:
    """100-letter words: one, its reverse, and one with a single letter changed."""
    w = word(random.Random(29), 100, 100)
    changed = w[:-1] + ("a" if w[-1] != "a" else "b")
    return [w, w[::-1], changed]


HIDDEN = [
    {"name": "no words", "args": ([],), "expect": []},
    {"name": "one word", "args": (["a"],), "expect": [["a"]]},
    {"name": "several empty strings", "args": (["", "", "a"],), "expect": [["", ""], ["a"]]},
    {"name": "repeated words", "args": (["ab", "ab", "ba"],), "expect": [["ab", "ab", "ba"]]},
    {
        "name": "same letters, different counts",
        "args": (["aab", "abb", "bab", "bba", "ab"],),
        "expect": [["aab"], ["abb", "bab", "bba"], ["ab"]],
    },
    {"name": "no anagrams at all", "args": (["abc", "def", "ghi"],)},
    {"name": "one big group", "args": (["abc", "bca", "cab", "acb", "bac", "cba"],)},
    {
        "name": "counts 1 and 11 against 11 and 1",
        "args": (["abbbbbbbbbbb", "aaaaaaaaaaab"],),
        "expect": [["abbbbbbbbbbb"], ["aaaaaaaaaaab"]],
    },
    {"name": "single letters", "args": (["a", "b", "a"],), "expect": [["a", "a"], ["b"]]},
    {"name": "100-letter words", "args": (long_words(),)},
    {
        "name": "the whole alphabet",
        "args": ([string.ascii_lowercase, string.ascii_lowercase[::-1], "zyx", "xyz", "q"],),
    },
    {
        "name": "12,000 words, some anagram groups",
        "args": (some_groups(12_000, 29),),
        "limit_ms": 500,
    },
    {
        "name": "10,000 words, no two anagrams",
        "args": (no_two_anagrams(10_000, 30),),
        "limit_ms": 500,
    },
]


def brute(strs):
    """Pairwise: each word joins the first group whose first word has the same sorted letters."""
    groups: list[list[str]] = []
    for w in strs:
        for group in groups:
            if sorted(group[0]) == sorted(w):
                group.append(w)
                break
        else:
            groups.append([w])
    return groups


def naive(strs):
    """The O(n²) approach the large tests must reject: a sorted key per word (computed once), but
    the groups are found by scanning a list of keys instead of looking the key up in a dict."""
    keys: list[str] = []
    groups: list[list[str]] = []
    for w in strs:
        key = "".join(sorted(w))
        for i, k in enumerate(keys):
            if k == key:
                groups[i].append(w)
                break
        else:
            keys.append(key)
            groups.append([w])
    return groups


def random_cases(rng: random.Random):
    for _ in range(300):  # a small alphabet and short words, so anagrams are common
        yield (
            [
                "".join(rng.choice("abc") for _ in range(rng.randint(0, 4)))
                for _ in range(rng.randint(0, 8))
            ],
        )
