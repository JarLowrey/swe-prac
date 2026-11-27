# The 8 moves from a cell: the 4 sides and the 4 diagonals.
STEPS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


class Solution:
    def shortestPathBinaryMatrix(self, grid: list[list[int]]) -> int:
        n = len(grid)
        # A clear path starts and ends on clear cells.
        if grid[0][0] == 1 or grid[n - 1][n - 1] == 1:
            return -1

        # Breadth-first search, one level at a time: `level` holds every cell whose shortest
        # path from the start has exactly `length` cells. The first level that contains the
        # bottom-right cell gives the answer.
        seen = [[False] * n for _ in range(n)]
        seen[0][0] = True
        level = [(0, 0)]
        length = 1  # the path to the start is just the start: one cell
        while level:
            next_level = []
            for r, c in level:
                if r == n - 1 and c == n - 1:
                    return length
                for dr, dc in STEPS:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] == 0 and not seen[nr][nc]:
                        # Mark when discovered, not when processed: another cell of this level
                        # may share this neighbour, and must not add it a second time.
                        seen[nr][nc] = True
                        next_level.append((nr, nc))
            level = next_level
            length += 1
        # The levels ran out without reaching the end: it is walled off.
        return -1
