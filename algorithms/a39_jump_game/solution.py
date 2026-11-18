class Solution:
    def canJump(self, nums: list[int]) -> bool:
        # If you can reach index j you can reach every index before it (a shorter jump from the
        # same place lands on it), so the reachable indices are always 0..reach. That single
        # number replaces the whole "can I get here?" DP table.
        reach = 0
        for i, jump in enumerate(nums):
            if i > reach:
                # No reachable index jumps as far as i, so neither i nor anything after it
                # (including the last index) can be reached.
                return False
            reach = max(reach, i + jump)  # i is reachable: extend by its own jump
        return True  # every index was within reach, the last one included
