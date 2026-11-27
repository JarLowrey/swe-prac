"""Tests for Remove Nth Node From End of List. The list is written as plain values; the method
returns the new head, which the test reads back as a list ("result": "listnode" in
problem.json)."""

import random

SHOWN = [
    {"name": "Example 1", "args": ([1, 2, 3, 4], 2), "expect": [1, 2, 4]},
    {"name": "Example 2", "args": ([1, 2, 3], 1), "expect": [1, 2]},
    {"name": "Example 3", "args": ([1], 1), "expect": []},
]

LONG = [random.Random(41).randint(0, 9) for _ in range(20_000)]

HIDDEN = [
    {"name": "remove the head", "args": ([1, 2, 3, 4, 5], 5), "expect": [2, 3, 4, 5]},
    {"name": "two nodes, remove the head", "args": ([1, 2], 2), "expect": [2]},
    {"name": "two nodes, remove the tail", "args": ([1, 2], 1), "expect": [1]},
    {"name": "remove the middle", "args": ([1, 2, 3, 4, 5], 3), "expect": [1, 2, 4, 5]},
    {"name": "remove the second node", "args": ([10, 20, 30, 40], 3), "expect": [10, 30, 40]},
    {
        "name": "remove the second-to-last",
        "args": ([5, 6, 7, 8, 9, 10], 2),
        "expect": [5, 6, 7, 8, 10],
    },
    {"name": "repeated values", "args": ([1, 2, 1, 2, 1], 2), "expect": [1, 2, 1, 1]},
    {"name": "all values equal", "args": ([0, 0, 0], 3), "expect": [0, 0]},
    {"name": "100 nodes, the 37th from the end", "args": (list(range(100)), 37)},
    {"name": "100 nodes, remove the head", "args": (list(range(100)), 100)},
    {"name": "20,000 nodes, remove the last", "args": (LONG, 1), "limit_ms": 500},
    {"name": "20,000 nodes, remove the middle", "args": (LONG, 10_000), "limit_ms": 500},
]


def brute(values, n):
    cut = len(values) - n  # the index of the node to remove
    return values[:cut] + values[cut + 1 :]


class _Node:
    def __init__(self, val, nxt=None):
        self.val, self.next = val, nxt


def naive(values, n):
    """The O(L^2) approach the large tests must reject: for each node, count the nodes after it;
    the one with n - 1 nodes after it is the one to remove."""
    head = None
    for v in reversed(values):
        head = _Node(v, head)
    before = dummy = _Node(None, head)
    while before.next:
        after, node = 0, before.next.next
        while node:
            after, node = after + 1, node.next
        if after == n - 1:
            before.next = before.next.next
            break
        before = before.next
    out, node = [], dummy.next
    while node:
        out.append(node.val)
        node = node.next
    return out


def random_cases(rng: random.Random):
    for length in range(1, 11):
        for _ in range(25):
            values = [rng.randint(0, 9) for _ in range(length)]
            yield (values, rng.randint(1, length))
