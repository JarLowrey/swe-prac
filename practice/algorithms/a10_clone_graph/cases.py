"""Tests for Clone Graph. A graph is written as an adjacency list: index i holds the neighbours of
the node with val i + 1. The runner builds the Node graph, calls cloneGraph with node 1, checks
that the copy shares no node with the original, and writes the copy back as an adjacency list.

A correct copy has exactly the input's adjacency list, which is what brute() returns. Any correct
approach is linear, so there is no time-limited test: the large graphs check correctness at scale
(and a recursion 1,000 calls deep along a path)."""

import random


def undirected(n, edges, rng=None):
    """Adjacency list for nodes 1..n from (a, b) edges. With rng, each neighbour list is shuffled
    so that no solution can rely on a sorted order."""
    adjacency = [[] for _ in range(n)]
    for a, b in edges:
        adjacency[a - 1].append(b)
        adjacency[b - 1].append(a)
    if rng is not None:
        for neighbours in adjacency:
            rng.shuffle(neighbours)
    return adjacency


def path(n):
    return undirected(n, [(i, i + 1) for i in range(1, n)])


def ring(n):
    return undirected(n, [(i, i % n + 1) for i in range(1, n + 1)])


def complete(n):
    return undirected(n, [(a, b) for a in range(1, n + 1) for b in range(a + 1, n + 1)])


def grid(rows, cols, seed):
    """A rows x cols grid of nodes, each joined to the nodes above, below, left and right."""

    def node(r, c):
        return r * cols + c + 1

    edges = [(node(r, c), node(r, c + 1)) for r in range(rows) for c in range(cols - 1)]
    edges += [(node(r, c), node(r + 1, c)) for r in range(rows - 1) for c in range(cols)]
    return undirected(rows * cols, edges, random.Random(seed))


def random_graph(rng, n, extra):
    """A random connected graph on 1..n: a random spanning tree plus up to `extra` more edges."""
    if n == 0:
        return []
    order = list(range(1, n + 1))
    rng.shuffle(order)
    edges = set()
    for i in range(1, n):
        a, b = order[i], order[rng.randrange(i)]
        edges.add((min(a, b), max(a, b)))
    if extra:
        spare = [(a, b) for a in range(1, n + 1) for b in range(a + 1, n + 1)]
        spare = [e for e in spare if e not in edges]
        edges.update(rng.sample(spare, min(extra, len(spare))))
    return undirected(n, sorted(edges), rng)


SHOWN = [
    {
        "name": "Example 1",
        "args": ([[2, 4], [1, 3], [2, 4], [1, 3]],),
        "expect": [[2, 4], [1, 3], [2, 4], [1, 3]],
    },
    {"name": "Example 2", "args": ([[]],), "expect": [[]]},
    {"name": "Example 3", "args": ([],), "expect": []},
]

HIDDEN = [
    {"name": "two nodes", "args": ([[2], [1]],), "expect": [[2], [1]]},
    {"name": "a triangle", "args": ([[2, 3], [1, 3], [1, 2]],)},
    {"name": "a path of 5 nodes", "args": (path(5),)},
    {"name": "a star around node 1", "args": (undirected(6, [(1, k) for k in range(2, 7)]),)},
    {"name": "a star around node 4", "args": (undirected(5, [(4, k) for k in (1, 2, 3, 5)]),)},
    {"name": "every pair joined, 6 nodes", "args": (complete(6),)},
    {
        "name": "neighbours in no particular order",
        "args": ([[3, 2, 4], [4, 1], [1, 4], [2, 3, 1]],),
        "expect": [[3, 2, 4], [4, 1], [1, 4], [2, 3, 1]],
    },
    {"name": "a ring of 12", "args": (ring(12),)},
    {
        "name": "two triangles sharing node 1",
        "args": (undirected(5, [(1, 2), (2, 3), (3, 1), (1, 4), (4, 5), (5, 1)]),),
    },
    {
        "name": "a tree-shaped graph",
        "args": (undirected(15, [(k // 2, k) for k in range(2, 16)], random.Random(10)),),
    },
    {"name": "a 30 x 30 grid", "args": (grid(30, 30, 11),)},
    {"name": "a path of 1,000 nodes", "args": (path(1000),)},
    {"name": "500 nodes, 1,500 edges", "args": (random_graph(random.Random(12), 500, 1001),)},
]


def brute(adjacency):
    """A deep copy is joined up exactly like the original."""
    return [list(neighbours) for neighbours in adjacency]


def random_cases(rng: random.Random):
    for n in range(11):
        for _ in range(25):
            yield (random_graph(rng, n, rng.randint(0, n)),)
