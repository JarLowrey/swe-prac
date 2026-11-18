"""Tests for Maximum Depth of Binary Tree. Trees are written in level order with None for a
missing child; the runner builds the TreeNode tree before calling maxDepth.

Every approach visits each node once, so there is no time-limited test: the large trees check
correctness at scale (and recursion 1,000 levels deep)."""

import random
from collections import deque

# Test trees are built as nested [value, left, right] lists, then written in level order.


def level_order(root):
    """Nested [value, left, right] lists to level order, with None for a missing child and the
    trailing Nones removed: the notation the tests use."""
    out, queue = [], deque([root])
    while queue:
        node = queue.popleft()
        if node is None:
            out.append(None)
            continue
        out.append(node[0])
        queue.append(node[1])
        queue.append(node[2])
    while out and out[-1] is None:
        out.pop()
    return out


def stick(n, turns, start=1):
    """A path of n nodes, each the only child of the one before. Node i+1 hangs off node i on
    the side turns[i % len(turns)] ('L' or 'R')."""
    root = node = [start, None, None]
    for i in range(1, n):
        child = [(start + i) % 100, None, None]
        node[1 if turns[(i - 1) % len(turns)] == "L" else 2] = child
        node = child
    return level_order(root)


def perfect(levels):
    """Every level full: in level order that is just 2^levels - 1 values, no gaps."""
    return [i % 10 for i in range(2**levels - 1)]


def random_tree(rng, n, low=-100, high=100):
    """n nodes in a random shape: each new node takes a random free child slot."""
    if n == 0:
        return []
    root = [rng.randint(low, high), None, None]
    slots = [(root, 1), (root, 2)]
    for _ in range(n - 1):
        k = rng.randrange(len(slots))
        slots[k], slots[-1] = slots[-1], slots[k]
        parent, side = slots.pop()
        child = [rng.randint(low, high), None, None]
        parent[side] = child
        slots += [(child, 1), (child, 2)]
    return level_order(root)


SHOWN = [
    {"name": "Example 1", "args": ([3, 9, 20, None, None, 15, 7],), "expect": 3},
    {"name": "Example 2", "args": ([1, None, 2, 3, 4],), "expect": 3},
    {"name": "Example 3", "args": ([],), "expect": 0},
]

HIDDEN = [
    {"name": "one node", "args": ([0],), "expect": 1},
    {"name": "a node with one child is not a leaf", "args": ([1, 2],), "expect": 2},
    {"name": "only left children", "args": (stick(5, "L"),), "expect": 5},
    {"name": "only right children", "args": (stick(4, "R"),), "expect": 4},
    {"name": "zigzag", "args": (stick(6, "LR"),), "expect": 6},
    {
        "name": "deepest leaf on the far left",
        "args": ([1, 2, 3, 4, None, None, None, 5],),
        "expect": 4,
    },
    {
        "name": "deepest leaf below the last node",
        "args": (
            [1, 2, 3, 4, 5, 6, 7, None, None, None, None, None, None, None, 8, 9, None, None, 10],
        ),
        "expect": 6,
    },
    {"name": "perfect tree, 15 nodes", "args": (perfect(4),), "expect": 4},
    {
        "name": "negative and repeated values",
        "args": ([-1, -1, -1, None, -1, None, -1, -1],),
        "expect": 4,
    },
    {"name": "perfect tree, 4,095 nodes", "args": (perfect(12),), "expect": 12},
    {"name": "1,000 levels", "args": (stick(1000, "LLR"),), "expect": 1000},
    {"name": "5,000 nodes, random shape", "args": (random_tree(random.Random(22), 5000, 0, 9),)},
]


def brute(values):
    """Each node's depth is its parent's plus one, read straight off the level-order list."""
    if not values or values[0] is None:
        return 0
    waiting = deque([1])  # depths of the nodes whose children come next in the list
    deepest, i = 1, 1
    while waiting and i < len(values):
        depth = waiting.popleft()
        for _ in range(2):  # the left child's slot, then the right child's
            if i < len(values) and values[i] is not None:
                waiting.append(depth + 1)
                deepest = max(deepest, depth + 1)
            i += 1
    return deepest


def random_cases(rng: random.Random):
    for n in range(16):
        for _ in range(12):
            yield (random_tree(rng, n),)
    for _ in range(30):
        yield (stick(rng.randint(1, 30), rng.choice(["L", "R", "LR", "LLR", "RRL"])),)
