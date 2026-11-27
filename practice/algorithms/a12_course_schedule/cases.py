"""Tests for Course Schedule. Expected outputs come from solution.py, checked against brute() (a
term-by-term simulation) on every small case and on random ones.

The time-limited tests are built so that a search without a "done" state (naive() below) never
finishes: in stacked diamonds each pair of courses unlocks both courses of the next pair, so the
number of routes doubles with every layer, and the same happens in random layers where each
course needs two or three courses of the layer before. Remembering finished courses makes the
search linear."""

import random


def diamonds(layers, start=0):
    """`layers` layers of two courses each, (start, start+1), (start+2, start+3), ...: both courses
    of one layer are prerequisites of both courses of the next."""
    pairs = []
    for k in range(layers - 1):
        for b in (start + 2 * k, start + 2 * k + 1):
            for a in (start + 2 * k + 2, start + 2 * k + 3):
                pairs.append([a, b])
    return pairs


def ring(courses):
    """Pairs making the given courses a cycle: each must come before the next, and the last
    before the first."""
    return [[courses[(i + 1) % len(courses)], c] for i, c in enumerate(courses)]


def shuffled(pairs, seed):
    out = list(pairs)
    random.Random(seed).shuffle(out)
    return out


def random_dag(rng, n, m):
    """m distinct pairs on n courses, all agreeing with a hidden random order, so no cycle."""
    order = list(range(n))
    rng.shuffle(order)
    rank = {course: i for i, course in enumerate(order)}
    pairs = set()
    while len(pairs) < m:
        a, b = rng.sample(range(n), 2)
        if rank[a] < rank[b]:
            a, b = b, a
        pairs.add((a, b))  # b comes before a in the hidden order
    out = [list(p) for p in sorted(pairs)]
    rng.shuffle(out)
    return out


def random_layers(rng, layers, width):
    """layers * width courses with shuffled labels. Each course after the first layer needs two
    or three random courses of the layer before: no cycle, but the routes multiply."""
    labels = list(range(layers * width))
    rng.shuffle(labels)
    pairs = []
    for k in range(1, layers):
        for i in range(width):
            course = labels[k * width + i]
            for j in rng.sample(range(width), rng.choice((2, 3))):
                pairs.append([course, labels[(k - 1) * width + j]])
    rng.shuffle(pairs)
    return pairs


SHOWN = [
    {"name": "Example 1", "args": (2, [[1, 0]]), "expect": True},
    {"name": "Example 2", "args": (2, [[1, 0], [0, 1]]), "expect": False},
    {"name": "Example 3", "args": (4, [[1, 0], [2, 0], [3, 1], [3, 2]]), "expect": True},
    {"name": "Example 4", "args": (5, [[1, 0], [3, 2], [4, 3], [2, 4]]), "expect": False},
]

HIDDEN = [
    {"name": "one course, no prerequisites", "args": (1, []), "expect": True},
    {"name": "no prerequisites at all", "args": (5, []), "expect": True},
    {"name": "a course that needs itself", "args": (1, [[0, 0]]), "expect": False},
    {
        "name": "a course that needs itself, mid-chain",
        "args": (4, [[1, 0], [2, 1], [2, 2], [3, 2]]),
        "expect": False,
    },
    {
        "name": "many courses share one prerequisite",
        "args": (6, [[c, 0] for c in range(1, 6)]),
        "expect": True,
    },
    {
        "name": "one course needs all the others",
        "args": (6, [[0, c] for c in range(1, 6)]),
        "expect": True,
    },
    {"name": "a cycle through all 8 courses", "args": (8, ring(list(range(8)))), "expect": False},
    {
        "name": "the cycle is out of reach of course 0",
        "args": (6, [[1, 0], [2, 1], *ring([3, 4, 5])]),
        "expect": False,
    },
    {
        "name": "the last pair closes a cycle",
        "args": (5, [[1, 0], [2, 1], [3, 2], [4, 3], [0, 4]]),
        "expect": False,
    },
    {
        "name": "routes meet without a cycle",
        "args": (12, shuffled(diamonds(6), 1)),
        "expect": True,
    },
    {
        "name": "1,000 courses in one chain",
        "args": (1000, shuffled([[c + 1, c] for c in range(999)], 2)),
        "expect": True,
    },
    {
        "name": "2,000 courses in stacked diamonds",
        "args": (2000, shuffled(diamonds(1000), 3)),
        "expect": True,
        "limit_ms": 500,
    },
    {
        "name": "2,000 courses in random layers",
        "args": (2000, random_layers(random.Random(12), 200, 10)),
        "expect": True,
        "limit_ms": 500,
    },
    {
        "name": "stacked diamonds, then a cycle in the last courses",
        "args": (2000, shuffled(diamonds(995) + ring(list(range(1990, 2000))), 4)),
        "expect": False,
        "limit_ms": 500,
    },
]


def brute(numCourses, prerequisites):
    """Simulate the terms: each term, take every course whose prerequisites have all been taken.
    When a term takes nothing, the answer is whether everything was taken."""
    needs = [set() for _ in range(numCourses)]
    for a, b in prerequisites:
        needs[a].add(b)
    taken = set()
    while True:
        term = [c for c in range(numCourses) if c not in taken and needs[c] <= taken]
        if not term:
            return len(taken) == numCourses
        taken.update(term)


def naive(numCourses, prerequisites):
    """The search without a done state: from every course, follow the arrows and report a cycle
    if the walk comes back to a course on its current path. Correct, but it walks every route
    separately, which is exponential on stacked diamonds."""
    unlocks = [[] for _ in range(numCourses)]
    for a, b in prerequisites:
        unlocks[b].append(a)
    on_path = [False] * numCourses

    def cycle_from(course):
        on_path[course] = True
        for nxt in unlocks[course]:
            if on_path[nxt] or cycle_from(nxt):
                return True
        on_path[course] = False
        return False

    return not any(cycle_from(c) for c in range(numCourses))


def comes_after(n, pairs, course):
    """Every course that course is (directly or not) a prerequisite of."""
    unlocks = [[] for _ in range(n)]
    for a, b in pairs:
        unlocks[b].append(a)
    seen, stack = set(), [course]
    while stack:
        for nxt in unlocks[stack.pop()]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def random_cases(rng: random.Random):
    for _ in range(300):
        n = rng.randint(1, 8)
        pairs = random_dag(rng, n, rng.randint(0, min(12, n * (n - 1) // 2))) if n > 1 else []
        r = rng.random()
        x = rng.randrange(n)
        later = sorted(comes_after(n, pairs, x) - {x})
        if r < 0.35 and later:  # x must also come after one of its successors: a sure cycle
            pairs.append([x, rng.choice(later)])
        elif r < 0.5 and n > 1:  # one more pair in a random direction: sometimes a cycle
            a, b = rng.sample(range(n), 2)
            if [a, b] not in pairs:
                pairs.append([a, b])
        elif r < 0.6:  # a course that needs itself
            pairs.append([x, x])
        rng.shuffle(pairs)
        yield (n, pairs)
