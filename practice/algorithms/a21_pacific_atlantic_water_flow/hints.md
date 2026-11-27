**Hint 1.** The direct approach: from every cell, search the cells its water can reach (steps to
neighbours that are no higher) and check whether the search touches both oceans. That is correct.
How much work is it on a 200 x 200 grid, where one search can cover the whole grid?

**Hint 2.** Turn the question round. Instead of asking where each cell's water goes, ask which
cells' water can arrive at the Pacific. Start at the cells along the Pacific edges and walk
*backwards*, against the flow.

**Hint 3.** Water flows from a cell to a neighbour that is no higher, so walking backwards you may
step to a neighbour that is **at least as high**. One search from all the Pacific edge cells at
once finds every cell that drains to the Pacific; do the same from the Atlantic edges.

**Hint 4.** The answer is the cells in both sets. Each search visits each cell at most once, so
the whole thing is O(m · n). Use one visited set per ocean, and an explicit stack or queue if you
are worried about recursion depth (a search can be m · n cells deep).
