"""Tests for Same Tree. Trees are written in level order with None for a missing child; the
runner builds both TreeNode trees before calling isSameTree.

Any correct approach is linear, so there is no time-limited test: the large trees check
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


def random_nested(rng, n, low, high):
    """n nodes in a random shape: each new node takes a random free child slot."""
    if n == 0:
        return None
    root = [rng.randint(low, high), None, None]
    slots = [(root, 1), (root, 2)]
    for _ in range(n - 1):
        k = rng.randrange(len(slots))
        slots[k], slots[-1] = slots[-1], slots[k]
        parent, side = slots.pop()
        child = [rng.randint(low, high), None, None]
        parent[side] = child
        slots += [(child, 1), (child, 2)]
    return root


def stick(n, turns):
    """A path of n nodes; node i+1 hangs off node i on the side turns[i % len(turns)]."""
    root = node = [1, None, None]
    for i in range(1, n):
        child = [(i + 1) % 100, None, None]
        node[1 if turns[(i - 1) % len(turns)] == "L" else 2] = child
        node = child
    return root


def clone(root):
    """An independent copy of a nested tree. Round-tripping through level order is iterative,
    unlike copy.deepcopy, which recurses once per level."""
    return parse(level_order(root))


def all_nodes(root):
    """(node, parent, side) for every node, in level order."""
    out, queue = [], deque([(root, None, 0)] if root else [])
    while queue:
        node, parent, side = queue.popleft()
        out.append((node, parent, side))
        for s in (1, 2):
            if node[s] is not None:
                queue.append((node[s], node, s))
    return out


def deepest_changed(root):
    """A copy whose last node in level order (a deepest leaf) holds a different value."""
    other = clone(root)
    node = all_nodes(other)[-1][0]
    node[0] += 1
    return other


def last_moved(root):
    """A copy whose last node in level order hangs on the other side of its parent."""
    other = clone(root)
    node, parent, side = all_nodes(other)[-1]
    parent[side], parent[3 - side] = None, node
    return other


def leaf_added(root):
    """A copy with one extra child under the last node in level order."""
    other = clone(root)
    all_nodes(other)[-1][0][1] = [5, None, None]
    return other


BIG = random_nested(random.Random(23), 3000, 0, 9)
TALL = stick(1000, "LRR")

SHOWN = [
    {"name": "Example 1", "args": ([1, 2, 3], [1, 2, 3]), "expect": True},
    {"name": "Example 2", "args": ([1, 2], [1, None, 2]), "expect": False},
    {"name": "Example 3", "args": ([1, 2, 1], [1, 1, 2]), "expect": False},
]

HIDDEN = [
    {"name": "both empty", "args": ([], []), "expect": True},
    {"name": "only p empty", "args": ([], [0]), "expect": False},
    {"name": "only q empty", "args": ([0], []), "expect": False},
    {"name": "one equal node", "args": ([7], [7]), "expect": True},
    {"name": "one node, different values", "args": ([7], [-7]), "expect": False},
    {"name": "zeros everywhere", "args": ([0, 0, None, 0], [0, 0, None, 0]), "expect": True},
    {"name": "a zero child is not a missing child", "args": ([0, 0], [0]), "expect": False},
    {"name": "mirror images", "args": ([1, 2, 3], [1, 3, 2]), "expect": False},
    {"name": "same in-order values", "args": ([2, 1], [1, None, 2]), "expect": False},
    {"name": "same pre-order values", "args": ([1, 2, 3], [1, 2, None, 3]), "expect": False},
    {"name": "3,000 identical nodes", "args": (level_order(BIG), level_order(BIG)), "expect": True},
    {
        "name": "3,000 nodes, the deepest leaf differs",
        "args": (level_order(BIG), level_order(deepest_changed(BIG))),
        "expect": False,
    },
    {
        "name": "3,000 nodes, one extra leaf",
        "args": (level_order(BIG), level_order(leaf_added(BIG))),
        "expect": False,
    },
    {
        "name": "1,000 levels, identical",
        "args": (level_order(TALL), level_order(TALL)),
        "expect": True,
    },
    {
        "name": "1,000 levels, the last node on the other side",
        "args": (level_order(TALL), level_order(last_moved(TALL))),
        "expect": False,
    },
]


def brute(p, q):
    """A level-order list with None markers identifies a tree, so compare the canonical lists
    (re-serialized, in case an input lists extra trailing Nones)."""
    return level_order(parse(p)) == level_order(parse(q))


def random_cases(rng: random.Random):
    for _ in range(400):
        a = random_nested(rng, rng.randint(0, 9), -2, 2)
        kind = rng.randrange(5)
        if kind == 0 or a is None:  # an identical copy
            b = clone(a)
        elif kind == 1:  # one value changed (sometimes to the same value)
            b = clone(a)
            rng.choice(all_nodes(b))[0][0] = rng.randint(-2, 2)
        elif kind == 2:  # one leaf removed, or one moved to the other side
            b = clone(a)
            leaves = [t for t in all_nodes(b) if t[1] is not None and t[0][1:] == [None, None]]
            if leaves:
                node, parent, side = rng.choice(leaves)
                parent[side] = None
                if rng.random() < 0.5 and parent[3 - side] is None:
                    parent[3 - side] = node
        elif kind == 3:  # one leaf added in a free child slot
            b = clone(a)
            free = [(node, s) for node, _, _ in all_nodes(b) for s in (1, 2) if node[s] is None]
            node, s = rng.choice(free)
            node[s] = [rng.randint(-2, 2), None, None]
        else:  # an unrelated tree
            b = random_nested(rng, rng.randint(0, 9), -2, 2)
        yield (level_order(a), level_order(b))
