class Solution:
    def combinationSum4(self, nums: list[int], target: int) -> int:
        # ways[t] = the number of ordered sequences of nums that add up to t.
        # A sequence for t starts with some x <= t, followed by any sequence for t - x, and
        # different first numbers give different sequences, so:
        #     ways[t] = sum(ways[t - x] for x in nums if x <= t)
        # ways[0] = 1: the empty sequence is the one way to finish when nothing is left.
        nums = sorted(nums)  # lets the inner loop stop at the first number that overshoots
        ways = [1] + [0] * target
        # The target loop is on the outside, so every first number is tried for every t and
        # 1 + 2 and 2 + 1 are both counted. (Numbers on the outside would count combinations.)
        for t in range(1, target + 1):
            total = 0
            for x in nums:
                if x > t:
                    break  # x, and every larger number, overshoots t
                total += ways[t - x]  # the sequences that start with x
            ways[t] = total
        return ways[target]
