from bisect import bisect_left


class Solution:
    def lengthOfLIS(self, nums: list[int]) -> int:
        # tails[k] = the smallest value that can end a strictly increasing subsequence of
        # length k + 1, among the numbers seen so far. A smaller tail is never worse: anything
        # that could follow a bigger tail could also follow it. tails is strictly increasing,
        # so each number's place in it can be found by binary search.
        #
        # (The O(n^2) dynamic programming answer is: ending[i] = 1 + max(ending[j]) over the
        # j < i with nums[j] < nums[i]; the result is max(ending). This is the O(n log n)
        # follow-up.)
        tails: list[int] = []
        for x in nums:
            # The first tail >= x. bisect_left (not bisect_right) keeps the run *strictly*
            # increasing: an equal value replaces its twin instead of extending the run.
            k = bisect_left(tails, x)
            if k == len(tails):
                tails.append(x)  # x is bigger than every tail: the longest run grows by one
            else:
                tails[k] = x  # a run of length k + 1 can now end in x, a smaller tail
        # tails may not be a real subsequence (for [3, 4, 1] it ends as [1, 4]), but its
        # length is the length of the longest one.
        return len(tails)
