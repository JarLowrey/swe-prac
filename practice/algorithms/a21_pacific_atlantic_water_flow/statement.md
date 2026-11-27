An island is an `m x n` grid of cells, and `heights[r][c]` is the height of the cell in row `r`,
column `c`. The Pacific Ocean touches the island's top and left edges; the Atlantic Ocean touches
its bottom and right edges.

When rain falls on a cell, the water can flow to any of the four neighbouring cells (up, down,
left, right) whose height is **less than or equal to** the current cell's. Water in a cell next to
an ocean can flow into that ocean.

Return the coordinates `[r, c]` of every cell from which rain water can reach **both** oceans, in
any order.

**Example 1**

```
Input:  heights = [[1, 2, 3, 4],
                   [2, 6, 7, 3],
                   [3, 5, 4, 2],
                   [4, 3, 2, 1]]
Output: [[0, 3], [1, 1], [1, 2], [2, 1], [3, 0]]
```

The top-right and bottom-left corners touch both oceans. Water on the 6, 7 and 5 in the middle
can run down to the top or left edge and also down to the bottom or right edge. Water on the 4 in
row 2 can only reach the Atlantic, since every way towards the Pacific goes uphill.

```grid
_ P P P P _
P 1 2 3 4 A
P 2 6 7 3 A
P 3 5 4 2 A
P 4 3 2 1 A
_ A A A A _
dim: 0,0 0,1 0,2 0,3 0,4 0,5 1,0 2,0 3,0 4,0 1,5 2,5 3,5 4,5 5,0 5,1 5,2 5,3 5,4 5,5
highlight: 1,4 2,2 2,3 3,2 4,1
caption: the island, ringed by its oceans (P above and left, A below and right)
```

**Example 2**

```
Input:  heights = [[1, 1, 1],
                   [1, 0, 1],
                   [1, 1, 1]]
Output: [[0, 0], [0, 1], [0, 2], [1, 0], [1, 2], [2, 0], [2, 1], [2, 2]]
```

Water on the edge cells can run along the equal heights to every edge. The 0 in the middle is
lower than all its neighbours, so its water stays where it is.

**Example 3**

```
Input:  heights = [[1, 1, 3],
                   [1, 2, 3],
                   [3, 3, 3]]
Output: [[0, 2], [1, 2], [2, 0], [2, 1], [2, 2]]
```

The wall of 3s along the bottom and right is higher than the cells inside it, so their water can
only reach the Pacific. The 3s themselves touch the Atlantic and can run along the wall to the
Pacific.

**Constraints**

- `1 <= m, n <= 200`
- `0 <= heights[r][c] <= 10^5`
