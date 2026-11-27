"""Tests for Invert Binary Tree. Trees are written in level order with None for a missing child;
the runner builds the TreeNode tree, calls invertTree and writes the returned tree back in level
order (checking that no node is reachable twice).

Every approach visits each node once, so there is no time-limited test: the large trees check
correctness at scale (and recursion 1,000 levels deep)."""

import random
from collections import deque

# Test trees are built as nested [value, left, right] lists, then written in level order.


def level_order(root, right_first=False):
    """Nested [value, left, right] lists to level order, with None for a missing child and the
    trailing Nones removed. right_first=True reads every node's children right to left."""
    out, queue = [], deque([root])
    while queue:
        node = queue.popleft()
        if node is None:
            out.append(None)
            continue
        out.append(node[0])
        first, second = (node[2], node[1]) if right_first else (node[1], node[2])
        queue.append(first)
        queue.append(second)
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
    {"name": "Example 1", "args": ([4, 2, 7, 1, 3, 6, 9],), "expect": [4, 7, 2, 9, 6, 3, 1]},
    {"name": "Example 2", "args": ([1, 2, 3, 4, 5],), "expect": [1, 3, 2, None, None, 5, 4]},
    {"name": "Example 3", "args": ([],), "expect": []},
]

HIDDEN = [
    {"name": "one node", "args": ([1],), "expect": [1]},
    {"name": "only a left child", "args": ([1, 2],), "expect": [1, None, 2]},
    {"name": "only a right child", "args": ([1, None, 2],), "expect": [1, 2]},
    {"name": "a left stick becomes a right stick", "args": (stick(4, "L"),)},
    {"name": "zigzag", "args": (stick(6, "LR"),)},
    {"name": "perfect tree, 15 nodes", "args": (list(range(1, 16)),)},
    {
        "name": "a symmetric tree is its own mirror",
        "args": ([1, 2, 2, 3, 4, 4, 3],),
        "expect": [1, 2, 2, 3, 4, 4, 3],
    },
    {
        "name": "gaps on both sides",
        "args": ([1, 2, 3, None, 4, 5],),
        "expect": [1, 3, 2, None, 5, 4],
    },
    {"name": "repeated values", "args": ([1, 1, 1, None, 1, 1],)},
    {"name": "negative values", "args": ([-1, -2, -3, -4, None, None, -5, -6],)},
    {"name": "1,000 levels", "args": (stick(1000, "LRL"),)},
    {"name": "3,000 nodes, random shape", "args": (random_tree(random.Random(24), 3000, 0, 9),)},
]


def brute(values):
    """The mirror image's level order is the original's level order with every node's children
    read right to left."""
    return level_order(parse(values), right_first=True)


def random_cases(rng: random.Random):
    for n in range(16):
        for _ in range(12):
            yield (random_tree(rng, n, -9, 9),)
    for _ in range(30):
        yield (stick(rng.randint(1, 25), rng.choice(["L", "R", "LR", "RRL"])),)
