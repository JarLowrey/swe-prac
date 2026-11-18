Given an `n x n` binary matrix `grid`, return the length of the **shortest clear path** from the
top-left cell `(0, 0)` to the bottom-right cell `(n - 1, n - 1)`, or `-1` if there is no such
path.

A clear path visits only cells that hold `0`. Each step moves to one of the **8** neighbouring
cells: up, down, left, right, or diagonally. The length of a path is the number of cells it
visits, counting the first and the last.

**Example 1**

```
Input:  grid = [[0, 1],
                [1, 0]]
Output: 2
```

One diagonal step: `(0, 0)` → `(1, 1)`.

```grid
0 1
1 0
path: 0,0 1,1
caption: 2 cells
```

**Example 2**

```
Input:  grid = [[0, 0, 0],
                [0, 1, 0],
                [0, 0, 0]]
Output: 4
```

The middle is blocked, so the path goes round it, cutting the corner with a diagonal step.

```grid
0 0 0
0 1 0
0 0 0
path: 0,0 0,1 1,2 2,2
caption: (0, 0) → (0, 1) → (1, 2) → (2, 2): 4 cells
```

**Example 3**

```
Input:  grid = [[0, 1, 0, 0, 0],
                [0, 1, 0, 1, 0],
                [0, 1, 0, 1, 0],
                [0, 0, 0, 1, 0],
                [1, 1, 1, 1, 0]]
Output: 11
```

The walls force the path down, back up, and down again.

```grid
0 1 0 0 0
0 1 0 1 0
0 1 0 1 0
0 0 0 1 0
1 1 1 1 0
path: 0,0 1,0 2,0 3,1 2,2 1,2 0,3 1,4 2,4 3,4 4,4
caption: the shortest way through visits 11 cells
```

**Example 4**

```
Input:  grid = [[1, 0, 0],
                [1, 1, 0],
                [1, 1, 0]]
Output: -1
```

The starting cell itself is blocked.

**Constraints**

- `1 <= n <= 100`, and `grid` is `n x n`.
- Every `grid[r][c]` is `0` or `1`.
