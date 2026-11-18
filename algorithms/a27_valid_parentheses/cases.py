"""Tests for Valid Parentheses."""

import random

SHOWN = [
    {"name": "Example 1", "args": ("()[]{}",), "expect": True},
    {"name": "Example 2", "args": ("{[()]}",), "expect": True},
    {"name": "Example 3", "args": ("(]",), "expect": False},
    {"name": "Example 4", "args": ("([)]",), "expect": False},
]

CLOSER = {"(": ")", "[": "]", "{": "}"}

HIDDEN = [
    {"name": "empty string", "args": ("",), "expect": True},
    {"name": "one opening bracket", "args": ("(",), "expect": False},
    {"name": "one closing bracket", "args": (")",), "expect": False},
    {"name": "openers only, even length", "args": ("[{",), "expect": False},
    {"name": "counts balance, order doesn't", "args": ("))((",), "expect": False},
    {"name": "wrong closing type", "args": ("(}",), "expect": False},
    {"name": "crossed pairs", "args": ("({)}",), "expect": False},
    {"name": "closer with an empty stack in the middle", "args": ("([]))(",), "expect": False},
    {"name": "nested and sequential", "args": ("(([]){})",), "expect": True},
    {"name": "closes in the wrong order", "args": ("[({])}",), "expect": False},
    {"name": "valid except the last character", "args": ("{[()()]}[]({)",), "expect": False},
    {"name": "10,000 pairs in a row", "args": ("()" * 5000,), "expect": True},
    {
        "name": "40,000 nested pairs",
        "args": ("[" * 20000 + "(" * 20000 + ")" * 20000 + "]" * 20000,),
        "expect": True,
        "limit_ms": 500,
    },
    {
        "name": "deep nesting, wrong last bracket",
        "args": ("(" * 40000 + ")" * 39999 + "]",),
        "expect": False,
        "limit_ms": 500,
    },
]


def brute(s):
    """Delete adjacent matched pairs until nothing changes: valid exactly when nothing is left.
    O(n²) on deep nesting (one or two pairs per pass), which the large tests reject."""
    while True:
        shorter = s.replace("()", "").replace("[]", "").replace("{}", "")
        if shorter == s:
            return s == ""
        s = shorter


def random_valid(rng: random.Random, pairs: int) -> str:
    out, stack = [], []
    while pairs or stack:
        if pairs and (not stack or rng.random() < 0.5):
            c = rng.choice("([{")
            out.append(c)
            stack.append(c)
            pairs -= 1
        else:
            out.append(CLOSER[stack.pop()])
    return "".join(out)


def random_cases(rng: random.Random):
    for _ in range(150):  # anything goes: mostly invalid
        yield ("".join(rng.choice("()[]{}") for _ in range(rng.randint(0, 10))),)
    for _ in range(150):  # valid strings
        yield (random_valid(rng, rng.randint(0, 6)),)
    for _ in range(150):  # valid strings with one character changed or two swapped
        s = list(random_valid(rng, rng.randint(1, 6)))
        i, j = rng.randrange(len(s)), rng.randrange(len(s))
        if rng.random() < 0.5:
            s[i] = rng.choice("()[]{}")
        else:
            s[i], s[j] = s[j], s[i]
        yield ("".join(s),)
