**Hint 1.** Think of the grid as a graph: every clear cell is a node, joined to its clear
neighbours (up to 8 of them). Every step costs the same. Which search finds shortest paths in a
graph like that?

**Hint 2.** Breadth-first search explores in order of distance: first every cell one step from the
start, then every cell two steps away, and so on. So the first time it reaches the bottom-right
cell, it got there along a shortest path. A depth-first search finds *a* path, not necessarily the
shortest.

**Hint 3.** Count the length by levels: process the cells one level at a time (or store each
cell's length when you discover it). Mark a cell as seen when you *add* it to the queue, not when
you take it out, or the same cell gets queued several times.

**Hint 4.** Handle the edges first: if the start or the end cell is blocked, return -1. A 1 x 1
grid holding `0` has a path of length 1.
