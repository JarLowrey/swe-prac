class Solution:
    def productExceptSelf(self, nums: list[int]) -> list[int]:
        # answer[i] = (product of everything left of i) * (product of everything right of i).
        # Both sides are running products, so two passes replace the O(n²) recomputation.
        n = len(nums)
        answer = [1] * n  # 1 changes nothing when multiplied, like 0 when added

        left = 1  # product of nums[0..i-1]: nothing yet, so 1
        for i in range(n):
            answer[i] = left  # write first, so nums[i] is not included...
            left *= nums[i]  # ...then extend the product for the next slot

        right = 1  # product of nums[i+1..n-1]
        for i in range(n - 1, -1, -1):
            answer[i] *= right  # left part (already stored) times right part
            right *= nums[i]

        # Zeros need no special case, and n = 0 or 1 falls out of the loops: [] and [1].
        return answer
