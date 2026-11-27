class Solution:
    def longestConsecutive(self, nums: list[int]) -> int:
        # A set answers "is v present?" in O(1) on average, and drops duplicates.
        values = set(nums)
        best = 0  # stays 0 for an empty array

        # Loop over the set, not nums: a start value repeated many times in nums would otherwise
        # walk the same run once per copy.
        for x in values:
            if x - 1 in values:
                continue  # x is inside a run; the walk from that run's start counts it

            # x starts a run: walk upwards while the next value is present.
            end = x
            while end + 1 in values:
                end += 1
            # Each value is walked over only from its own run's start, so all the walks together
            # take at most n steps: O(n) overall.
            best = max(best, end - x + 1)  # x..end inclusive holds end - x + 1 values

        return best
