"""Helpers for scratch.py in algorithm sessions, copied next to solution.py as helpers.py.

They build linked lists, trees and graphs from plain lists (the notation the examples use) and
turn them back into lists for printing. They use your solution's ListNode / TreeNode / Node
classes when it defines them.
"""

from collections import deque

import solution


class _ListNode:
    def __init__(self, val=0, next=None):  # noqa: A002
        self.val = val
        self.next = next


class _TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class _Node:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []


def _cls(name, fallback):
    return getattr(solution, name, fallback)


def make_list(values):
    """[1, 2, 3] -> 1 -> 2 -> 3 (returns the head, or None for [])."""
    head = None
    for value in reversed(values):
        node = _cls("ListNode", _ListNode)(value)
        node.next = head
        head = node
    return head


def make_lists(lists):
    """[[1, 4], [2]] -> a list of linked lists."""
    return [make_list(values) for values in lists]


def list_values(head, limit=10_000):
    out = []
    while head is not None and len(out) < limit:
        out.append(head.val)
        head = head.next
    if head is not None:
        out.append("...")  # a cycle, or a very long list
    return out


def make_tree(values):
    """Level order with None for a missing child: [1, None, 2] is 1 with a right child 2."""
    if not values or values[0] is None:
        return None
    cls = _cls("TreeNode", _TreeNode)

    def node(value):
        n = cls(value)
        n.left = n.right = None
        return n

    root = node(values[0])
    queue, i = deque([root]), 1
    while queue and i < len(values):
        parent = queue.popleft()
        for side in ("left", "right"):
            if i < len(values) and values[i] is not None:
                child = node(values[i])
                setattr(parent, side, child)
                queue.append(child)
            i += 1
    return root


def tree_values(root):
    out, queue = [], deque([root])
    while queue:
        n = queue.popleft()
        out.append(None if n is None else n.val)
        if n is not None:
            queue.extend((n.left, n.right))
    while out and out[-1] is None:
        out.pop()
    return out


def make_graph(adjacency):
    """Node i+1's neighbours are adjacency[i]; returns node 1 (or None for an empty graph)."""
    cls = _cls("Node", _Node)
    nodes = [cls(i + 1) for i in range(len(adjacency))]
    for node, neighbours in zip(nodes, adjacency, strict=True):
        node.neighbors = [nodes[v - 1] for v in neighbours]
    return nodes[0] if nodes else None


def graph_values(start):
    """Back to the adjacency-list notation, ordered by node value."""
    seen, queue, nodes = set(), deque([start] if start else []), {}
    while queue:
        n = queue.popleft()
        if id(n) in seen:
            continue
        seen.add(id(n))
        nodes[n.val] = n
        queue.extend(n.neighbors)
    return [[m.val for m in nodes[v].neighbors] for v in sorted(nodes)]
