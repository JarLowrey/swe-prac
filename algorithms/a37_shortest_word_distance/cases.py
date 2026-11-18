"""Tests for Shortest Word Distance."""

import random

SENTENCE = ["the", "quick", "brown", "fox", "quick"]

SHOWN = [
    {"name": "Example 1", "args": (SENTENCE, "the", "fox"), "expect": 3},
    {"name": "Example 2", "args": (SENTENCE, "quick", "fox"), "expect": 1},
    {"name": "Example 3", "args": (["a", "b", "c", "d", "c", "a"], "a", "c"), "expect": 1},
]


def closest_at_the_end() -> list[str]:
    """a's on the even indices of the first half, b's on the even indices of the second, and a
    final "b", "a": the only pair at distance 1 is the last two words."""
    first = ["a" if i % 2 == 0 else "x" for i in range(10_000)]
    second = ["b" if i % 2 == 0 else "x" for i in range(9_998)]
    return first + second + ["b", "a"]


HIDDEN = [
    {"name": "only the two words", "args": (["a", "b"], "a", "b"), "expect": 1},
    {"name": "word2 comes first", "args": (["b", "x", "a"], "a", "b"), "expect": 2},
    {"name": "neighbours near the end", "args": (["a", "b", "c", "b", "a"], "a", "b"), "expect": 1},
    {"name": "many copies of word1", "args": (["a", "a", "a", "x", "b"], "a", "b"), "expect": 2},
    {"name": "latest copy matters", "args": (["c", "x", "c", "a"], "a", "c"), "expect": 1},
    {
        "name": "closest pair is not the first of each",
        "args": (["a", "x", "x", "b", "x", "a", "b"], "a", "b"),
        "expect": 1,
    },
    {
        "name": "words that start the same",
        "args": (["make", "x", "makes", "make"], "make", "makes"),
        "expect": 1,
    },
    {
        "name": "answer at the start",
        "args": (["a", "b", "x", "x", "x", "a", "x", "x", "x", "b"], "a", "b"),
        "expect": 1,
    },
    {"name": "far apart", "args": (["a"] + ["x"] * 8 + ["b"], "a", "b"), "expect": 9},
    {
        "name": "longer words",
        "args": (["practice", "makes", "perfect", "coding", "makes"], "coding", "practice"),
        "expect": 3,
    },
    {
        "name": "20,000 words in two blocks",
        "args": (["a"] * 10_000 + ["b"] * 10_000, "a", "b"),
        "expect": 1,
        "limit_ms": 500,
    },
    {
        "name": "20,000 words, closest pair at the end",
        "args": (closest_at_the_end(), "b", "a"),
        "expect": 1,
        "limit_ms": 500,
    },
]


def brute(wordsDict, word1, word2):
    """Every pair of positions: O(n²) when both words are common, which the large tests reject."""
    p1 = [i for i, w in enumerate(wordsDict) if w == word1]
    p2 = [i for i, w in enumerate(wordsDict) if w == word2]
    return min(abs(i - j) for i in p1 for j in p2)


def random_cases(rng: random.Random):
    made = 0
    while made < 300:
        words = [rng.choice(["a", "b", "c", "ab"]) for _ in range(rng.randint(2, 12))]
        present = sorted(set(words))
        if len(present) < 2:
            continue
        word1, word2 = rng.sample(present, 2)
        made += 1
        yield (words, word1, word2)
