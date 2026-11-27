"""Tests for Reorder List. The list is written as plain values; the method reorders it in place
and the test reads the list from head afterwards ("check": "arg0" in problem.json)."""

import random

SHOWN = [
    {"name": "Example 1", "args": ([1, 2, 3, 4],), "expect": [1, 4, 2, 3]},
    {"name": "Example 2", "args": ([1, 2, 3, 4, 5],), "expect": [1, 5, 2, 4, 3]},
]

HIDDEN = [
    {"name": "empty list", "args": ([],), "expect": []},
    {"name": "one node", "args": ([7],), "expect": [7]},
    {"name": "two nodes", "args": ([1, 2],), "expect": [1, 2]},
    {"name": "three nodes", "args": ([1, 2, 3],), "expect": [1, 3, 2]},
    {"name": "seven nodes", "args": ([5, 6, 7, 8, 9, 10, 11],), "expect": [5, 11, 6, 10, 7, 9, 8]},
    {"name": "repeated values", "args": ([2, 2, 1, 1, 2, 2],)},
    {"name": "descending", "args": ([9, 8, 7, 6, 5, 4, 3, 2],)},
    {"name": "100 nodes", "args": (list(range(100)),)},
    {
        "name": "30,001 nodes",
        "args": ([random.Random(40).randint(1, 9) for _ in range(30_001)],),
        "limit_ms": 500,
    },
]


def brute(values):
    out, lo, hi = [], 0, len(values) - 1
    while lo <= hi:
        out.append(values[lo])
        if lo != hi:
            out.append(values[hi])
        lo, hi = lo + 1, hi - 1
    return out


class _Node:
    def __init__(self, val, nxt=None):
        self.val, self.next = val, nxt


def naive(values):
    """The O(n²) approach the large test must reject: repeatedly walk to the tail and move it
    forward."""
    head = None
    for v in reversed(values):
        head = _Node(v, head)
    cur = head
    while cur and cur.next and cur.next.next:
        prev = cur
        while prev.next.next:
            prev = prev.next
        last, prev.next = prev.next, None
        last.next, cur.next = cur.next, last
        cur = last.next


def random_cases(rng: random.Random):
    for n in range(12):
        for _ in range(15):
            yield ([rng.randint(1, 9) for _ in range(n)],)
