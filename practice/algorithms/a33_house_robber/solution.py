class Solution:
    def rob(self, nums: list[int]) -> int:
        # best(i) = the most money from houses i, i+1, ..., n-1. At house i, either
        #   rob it:  nums[i] + best(i + 2)   (house i + 1 is then off limits), or
        #   skip it: best(i + 1).
        # Past the last house there is nothing left: best(n) = best(n + 1) = 0.
        #
        # Filling best() from the last house back to the first, each step reads only the next
        # two values, so two variables replace the whole table: O(n) time, O(1) space.
        after1 = after2 = 0  # best(i + 1) and best(i + 2)
        for i in range(len(nums) - 1, -1, -1):
            best_here = max(nums[i] + after2, after1)  # rob house i, or skip it
            after1, after2 = best_here, after1  # slide one house towards the front
        return after1  # best(0): the whole street
