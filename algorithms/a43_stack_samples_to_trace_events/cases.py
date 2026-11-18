"""Tests for Convert Stack Samples to Trace Events. Samples and events are written as lists; the
runner turns returned tuples into lists, so a solution may return either."""

import random

SHOWN = [
    {
        "name": "Example 1",
        "args": ([[1, ["A"]], [2, ["A", "B"]], [3, ["A", "C"]], [4, ["A"]]],),
        "expect": [
            ["start", 1, "A"],
            ["start", 2, "B"],
            ["end", 3, "B"],
            ["start", 3, "C"],
            ["end", 4, "C"],
        ],
    },
    {
        "name": "Example 2",
        "args": ([[1, ["main", "foo"]], [2, ["main", "foo"]], [3, ["main"]]],),
        "expect": [["start", 1, "main"], ["start", 1, "foo"], ["end", 3, "foo"]],
    },
    {
        "name": "Example 3",
        "args": ([[1, ["main", "f", "g"]], [2, ["main", "h", "g"]]],),
        "expect": [
            ["start", 1, "main"],
            ["start", 1, "f"],
            ["start", 1, "g"],
            ["end", 2, "g"],
            ["end", 2, "f"],
            ["start", 2, "h"],
            ["start", 2, "g"],
        ],
    },
]


def deep_recursion(depth: int, samples: int) -> list:
    """main plus a recursion depth - 2 calls deep, sampled while the innermost call alternates
    between g and h. Every frame starts once; after that each sample ends one call and starts
    one. Identifying calls by their full path costs O(depth²) a sample."""
    base = ["main"] + ["f"] * (depth - 2)
    return [[t + 1, base + ["g" if t % 2 else "h"]] for t in range(samples)]


HIDDEN = [
    {"name": "no samples", "args": ([],), "expect": []},
    {"name": "one empty sample", "args": ([[1, []]],), "expect": []},
    {
        "name": "one sample",
        "args": ([[5, ["main", "a", "b"]]],),
        "expect": [["start", 5, "main"], ["start", 5, "a"], ["start", 5, "b"]],
    },
    {
        "name": "recursion grows and unwinds",
        "args": ([[1, ["f"]], [2, ["f", "f"]], [3, ["f", "f", "f"]], [4, ["f"]]],),
        "expect": [
            ["start", 1, "f"],
            ["start", 2, "f"],
            ["start", 3, "f"],
            ["end", 4, "f"],
            ["end", 4, "f"],
        ],
    },
    {
        "name": "idle between calls",
        "args": ([[1, ["a"]], [2, []], [3, ["a"]]],),
        "expect": [["start", 1, "a"], ["end", 2, "a"], ["start", 3, "a"]],
    },
    {
        "name": "everything changes",
        "args": ([[1, ["a", "b"]], [2, ["c", "d"]]],),
        "expect": [
            ["start", 1, "a"],
            ["start", 1, "b"],
            ["end", 2, "b"],
            ["end", 2, "a"],
            ["start", 2, "c"],
            ["start", 2, "d"],
        ],
    },
    {
        "name": "identical samples",
        "args": ([[1, ["m", "x"]], [2, ["m", "x"]], [3, ["m", "x"]]],),
        "expect": [["start", 1, "m"], ["start", 1, "x"]],
    },
    {
        "name": "same names above a new caller",
        "args": ([[1, ["m", "a", "x", "y"]], [2, ["m", "b", "x", "y"]]],),
    },
    {"name": "several calls start at once", "args": ([[1, ["m"]], [2, ["m", "a", "b", "c"]]],)},
    {"name": "several calls end at once", "args": ([[1, ["m", "a", "b", "c"]], [2, ["m"]]],)},
    {"name": "recursion with a new top", "args": ([[1, ["f", "f", "g"]], [2, ["f", "f", "f"]]],)},
    {
        "name": "time 0 and large timestamps",
        "args": ([[0, ["a"]], [10**9 - 1, ["a", "b"]], [10**9, ["b"]]],),
    },
    {
        "name": "a profile of a small program",
        "args": (
            [
                [1, ["main"]],
                [2, ["main", "parse"]],
                [3, ["main", "parse", "read"]],
                [4, ["main", "eval"]],
                [5, ["main", "eval"]],
                [6, []],
            ],
        ),
    },
    {
        "name": "recursion 7,000 calls deep",
        "args": (deep_recursion(7_000, 3),),
        "limit_ms": 500,
    },
]


def brute(samples):
    """Straight from the definition: a frame at depth d is the same call in both samples exactly
    when the stacks agree on depths 0..d."""
    events, prev = [], []
    for time, stack in samples:
        for d in reversed(range(len(prev))):
            if not (d < len(stack) and prev[: d + 1] == stack[: d + 1]):
                events.append(["end", time, prev[d]])
        for d in range(len(stack)):
            if not (d < len(prev) and prev[: d + 1] == stack[: d + 1]):
                events.append(["start", time, stack[d]])
        prev = stack
    return events


def naive(samples):
    """The plausible slow approach: identify each call by its full path and diff the sets of
    paths. Correct, but O(depth²) time and memory a sample."""
    events, prev_paths = [], []
    for time, stack in samples:
        paths = [tuple(stack[: d + 1]) for d in range(len(stack))]
        seen_now, seen_before = set(paths), set(prev_paths)
        events += [("end", time, p[-1]) for p in reversed(prev_paths) if p not in seen_now]
        events += [("start", time, p[-1]) for p in paths if p not in seen_before]
        prev_paths = paths
    return events


def random_cases(rng: random.Random):
    for _ in range(300):
        samples, stack, time = [], [], 0
        for _ in range(rng.randint(0, 8)):
            # Pop a few frames, push a few, sometimes leave the stack as it was.
            for _ in range(rng.randint(0, len(stack))):
                stack.pop()
            for _ in range(rng.randint(0, 3)):
                stack.append(rng.choice("abf"))
            time += rng.randint(1, 3)
            samples.append([time, list(stack)])
        yield (samples,)
