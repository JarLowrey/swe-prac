class Solution:
    def pacificAtlantic(self, heights: list[list[int]]) -> list[list[int]]:
        if not heights or not heights[0]:
            return []  # no cells (the constraints rule this out, but it costs nothing)
        rows, cols = len(heights), len(heights[0])

        def climb(starts: list[tuple[int, int]]) -> set[tuple[int, int]]:
            """Every cell whose water can reach one of the start cells, and so that ocean.

            Water flows from a cell to a neighbour that is no higher. This walks the flow
            backwards: from a cell, step to any neighbour that is at least as high. All the
            start cells go on the stack at once: one search per ocean, not one per edge cell.
            """
            reached = set(starts)  # a set: the corners appear in two edge lists
            stack = list(reached)  # an explicit stack: recursion could go rows * cols deep
            while stack:
                r, c = stack.pop()
                for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                    if (
                        0 <= nr < rows
                        and 0 <= nc < cols
                        and (nr, nc) not in reached  # each cell is processed once per ocean
                        and heights[nr][nc] >= heights[r][c]  # uphill or level, against the flow
                    ):
                        reached.add((nr, nc))
                        stack.append((nr, nc))
            return reached

        # The Pacific touches the top row and the left column, the Atlantic the bottom row and
        # the right column. Each search has its own reached set.
        pacific = climb([(0, c) for c in range(cols)] + [(r, 0) for r in range(rows)])
        atlantic = climb(
            [(rows - 1, c) for c in range(cols)] + [(r, cols - 1) for r in range(rows)]
        )
        # The cells whose water reaches both. Any order is accepted; sorted reads row by row.
        return [[r, c] for r, c in sorted(pacific & atlantic)]
