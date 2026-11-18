"""Tests for Binary Tree Level Order Traversal. Trees are written in level order with None for a
missing child; the runner builds the TreeNode tree before calling levelOrder.

The time-limited test is a perfect tree of 8,191 nodes with a 987-node tail: one walk from the
root per level (naive() below) passes through the perfect part once per level, about 8.6 million
visits (about 0.9 s), while BFS visits each node once (about 1 ms). The input can't grow much
more (it is already about 80 KB of JSON and 1,000 levels deep), so the limit is 250 ms rather
than 500."""

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


def parse(values):
    """Level order back to nested [value, left, right] lists (None for an empty tree)."""
    if not values or values[0] is None:
        return None
    root = [values[0], None, None]
    queue, i = deque([root]), 1
    while queue and i < len(values):
        node = queue.popleft()
        for side in (1, 2):
            if i < len(values) and values[i] is not None:
                node[side] = [values[i], None, None]
                queue.append(node[side])
            i += 1
    return root


def stick(n, turns):
    """A path of n nodes; node i+1 hangs off node i on the side turns[i % len(turns)]."""
    root = node = [1, None, None]
    for i in range(1, n):
        child = [(i + 1) % 100, None, None]
        node[1 if turns[(i - 1) % len(turns)] == "L" else 2] = child
        node = child
    return level_order(root)


def broom(levels, tail):
    """A perfect tree of `levels` levels with a zigzag of `tail` more nodes below its leftmost
    leaf: many shallow nodes and a great height, the worst case for one walk per level."""
    nodes = [[i % 10, None, None] for i in range(2**levels - 1)]
    for i, node in enumerate(nodes):
        if 2 * i + 2 < len(nodes):
            node[1], node[2] = nodes[2 * i + 1], nodes[2 * i + 2]
    node = nodes[2 ** (levels - 1) - 1]  # the leftmost leaf
    for i in range(tail):
        child = [i % 10, None, None]
        node[1 + i % 2] = child
        node = child
    return level_order(nodes[0])


def random_tree(rng, n, low=-1000, high=1000):
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
    {
        "name": "Example 1",
        "args": ([3, 9, 20, None, None, 15, 7],),
        "expect": [[3], [9, 20], [15, 7]],
    },
    {
        "name": "Example 2",
        "args": ([1, 2, 3, 4, None, None, 5],),
        "expect": [[1], [2, 3], [4, 5]],
    },
    {"name": "Example 3", "args": ([],), "expect": []},
]

HIDDEN = [
    {"name": "one node", "args": ([5],), "expect": [[5]]},
    {"name": "only left children", "args": (stick(4, "L"),), "expect": [[1], [2], [3], [4]]},
    {"name": "only right children", "args": (stick(3, "R"),), "expect": [[1], [2], [3]]},
    {"name": "zigzag", "args": (stick(6, "LR"),)},
    {
        "name": "perfect tree, 15 nodes",
        "args": (list(range(1, 16)),),
        "expect": [[1], [2, 3], [4, 5, 6, 7], [8, 9, 10, 11, 12, 13, 14, 15]],
    },
    {
        "name": "cousins share a level",
        "args": ([1, 2, 3, None, 4, 5],),
        "expect": [[1], [2, 3], [4, 5]],
    },
    {
        "name": "the left side is deeper",
        "args": ([1, 2, 3, 4, None, None, None, 5],),
        "expect": [[1], [2, 3], [4], [5]],
    },
    {"name": "zeros", "args": ([0, 0, 0, None, 0],), "expect": [[0], [0, 0], [0]]},
    {"name": "negative and repeated values", "args": ([-1, -1, 7, None, -1000, 7, -1],)},
    {"name": "1,000 levels", "args": (stick(1000, "LLR"),)},
    {"name": "5,000 nodes, random shape", "args": (random_tree(random.Random(25), 5000, 0, 9),)},
    {"name": "a perfect tree with a long tail", "args": (broom(13, 987),), "limit_ms": 250},
]


def brute(values):
    """Depth-first instead of breadth-first: a pre-order walk (node, left, right) meets each
    level's nodes from left to right, so append each value to the list for its depth."""
    root = parse(values)
    levels = []
    stack = [(root, 0)] if root else []
    while stack:
        node, depth = stack.pop()
        if depth == len(levels):
            levels.append([])
        levels[depth].append(node[0])
        for child in (node[2], node[1]):  # push right first, so left is visited first
            if child is not None:
                stack.append((child, depth + 1))
    return levels


def naive(values):
    """One walk per level: find the height, then for each depth walk down from the root and
    collect the nodes at that depth. Correct, but O(n * h)."""
    root = parse(values)

    def height(node):
        return 0 if node is None else 1 + max(height(node[1]), height(node[2]))

    def collect(node, depth, out):
        if node is None:
            return
        if depth == 0:
            out.append(node[0])
            return
        collect(node[1], depth - 1, out)
        collect(node[2], depth - 1, out)

    levels = []
    for depth in range(height(root)):
        level = []
        collect(root, depth, level)
        levels.append(level)
    return levels


def random_cases(rng: random.Random):
    for n in range(16):
        for _ in range(12):
            yield (random_tree(rng, n, -9, 9),)
    for _ in range(30):
        yield (stick(rng.randint(1, 25), rng.choice(["L", "R", "LR", "RRL"])),)
