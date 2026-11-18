class Solution:
    def climbStairs(self, n: int) -> int:
        # The last move onto stair i came from stair i - 1 (a 1-step) or stair i - 2 (a 2-step),
        # so ways(i) = ways(i - 1) + ways(i - 2). Base cases: ways(0) = 1 (already at the top is
        # one complete way) and ways(1) = 1.
        #
        # Filling the values from the ground up, each one needs only the two before it, so two
        # variables replace the whole table: O(n) time, O(1) space.
        before, current = 1, 1  # ways(i - 2) and ways(i - 1), starting with ways(0), ways(1)
        for _ in range(2, n + 1):
            # Both right-hand values are read before either name changes.
            before, current = current, before + current
        return current  # ways(n); for n = 1 the loop never runs and this is ways(1) = 1
