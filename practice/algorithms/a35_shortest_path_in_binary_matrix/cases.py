"""Tests for Shortest Path in Binary Matrix. Expected outputs come from solution.py, checked
against brute() (relax every cell's length until nothing changes) on every small case and on
random ones.

The time-limited tests defeat a depth-first search that revisits a cell whenever it finds a
shorter way there (naive() below): it is correct, but on large open areas it keeps redoing the
cells beyond each improvement and runs for many seconds, while BFS takes a few milliseconds."""

import random

STEPS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def open_grid(n):
    return [[0] * n for _ in range(n)]


def only_diagonal(n):
    """Clear on the main diagonal only."""
    return [[0 if r == c else 1 for c in range(n)] for r in range(n)]


def snake(n):
    """Walls hanging alternately from the top and the bottom edge, every other column: the path
    winds down and up between them."""
    grid = open_grid(n)
    for c in range(1, n - 1, 2):
        rows = range(0, n - 1) if c % 4 == 1 else range(1, n)
        for r in rows:
            grid[r][c] = 1
    return grid


def transpose(grid):
    return [list(row) for row in zip(*grid, strict=True)]


def walled_end(n):
    """Open, except for an L of walls that shuts the bottom-right 2 x 2 corner off."""
    grid = open_grid(n)
    for i in range(n - 3, n):
        grid[n - 3][i] = 1
        grid[i][n - 3] = 1
    return grid


def random_grid(seed, n, blocked):
    rng = random.Random(seed)
    grid = [[1 if rng.random() < blocked else 0 for _ in range(n)] for _ in range(n)]
    grid[0][0] = grid[n - 1][n - 1] = 0
    return grid


SHOWN = [
    {"name": "Example 1", "args": ([[0, 1], [1, 0]],), "expect": 2},
    {"name": "Example 2", "args": ([[0, 0, 0], [0, 1, 0], [0, 0, 0]],), "expect": 4},
    {
        "name": "Example 3",
        "args": (
            [
                [0, 1, 0, 0, 0],
                [0, 1, 0, 1, 0],
                [0, 1, 0, 1, 0],
                [0, 0, 0, 1, 0],
                [1, 1, 1, 1, 0],
            ],
        ),
        "expect": 11,
    },
    {"name": "Example 4", "args": ([[1, 0, 0], [1, 1, 0], [1, 1, 0]],), "expect": -1},
]

HIDDEN = [
    {"name": "one clear cell", "args": ([[0]],), "expect": 1},
    {"name": "one blocked cell", "args": ([[1]],), "expect": -1},
    {"name": "the end is blocked", "args": ([[0, 0], [0, 1]],), "expect": -1},
    {"name": "only diagonal steps get through", "args": (only_diagonal(6),), "expect": 6},
    {
        "name": "a crack only a diagonal step fits through",
        "args": ([[0, 1, 0], [1, 0, 1], [0, 1, 0]],),
        "expect": 3,
    },
    {
        "name": "a full wall across the middle",
        "args": ([[0, 0, 0, 0], [0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0]],),
        "expect": -1,
    },
    {"name": "all clear, 5 x 5", "args": (open_grid(5),), "expect": 5},
    {"name": "a winding path", "args": (snake(9),)},
    {"name": "a winding path, row by row", "args": (transpose(snake(10)),)},
    {"name": "random 12 x 12, a third blocked", "args": (random_grid(35, 12, 0.33),)},
    {"name": "random 15 x 15, a fifth blocked", "args": (random_grid(36, 15, 0.2),)},
    {"name": "100 x 100, all clear", "args": (open_grid(100),), "limit_ms": 500},
    {
        "name": "100 x 100, a quarter blocked",
        "args": (random_grid(37, 100, 0.25),),
        "limit_ms": 500,
    },
    {"name": "100 x 100, the end is walled off", "args": (walled_end(100),), "limit_ms": 500},
]


def brute(grid):
    """Give the start length 1, then keep relaxing every clear cell's neighbours (a neighbour is
    at most one longer) until nothing changes. Slow, but plainly the shortest length."""
    n = len(grid)
    if grid[0][0] == 1 or grid[n - 1][n - 1] == 1:
        return -1
    inf = float("inf")
    best = [[inf] * n for _ in range(n)]
    best[0][0] = 1
    changed = True
    while changed:
        changed = False
        for r in range(n):
            for c in range(n):
                if grid[r][c] == 1 or best[r][c] == inf:
                    continue
                for dr, dc in STEPS:
                    nr, nc = r + dr, c + dc
                    if (
                        0 <= nr < n
                        and 0 <= nc < n
                        and grid[nr][nc] == 0
                        and best[r][c] + 1 < best[nr][nc]
                    ):
                        best[nr][nc] = best[r][c] + 1
                        changed = True
    return best[n - 1][n - 1] if best[n - 1][n - 1] < inf else -1


def naive(grid):
    """Depth-first search that keeps the best length found for each cell and goes back into a
    cell whenever a shorter way to it turns up. Correct, but far too slow on open grids."""
    n = len(grid)
    if grid[0][0] == 1 or grid[n - 1][n - 1] == 1:
        return -1
    best = {(0, 0): 1}
    stack = [(0, 0)]
    while stack:
        r, c = stack.pop()
        length = best[(r, c)]
        for dr, dc in STEPS:
            nr, nc = r + dr, c + dc
            if (
                0 <= nr < n
                and 0 <= nc < n
                and grid[nr][nc] == 0
                and length + 1 < best.get((nr, nc), n * n + 1)
            ):
                best[(nr, nc)] = length + 1
                stack.append((nr, nc))
    return best.get((n - 1, n - 1), -1)


def random_cases(rng: random.Random):
    for _ in range(300):
        n = rng.randint(1, 7)
        blocked = rng.choice((0.0, 0.2, 0.35, 0.5))
        grid = [[1 if rng.random() < blocked else 0 for _ in range(n)] for _ in range(n)]
        if rng.random() < 0.85:  # usually keep both ends clear, so there is something to find
            grid[0][0] = grid[n - 1][n - 1] = 0
        yield (grid,)
