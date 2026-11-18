class Solution:
    def search(self, nums: list[int], target: int) -> int:
        # The rotated array is two sorted runs: first the values >= nums[0], then the values
        # < nums[0] (an empty run when the array isn't rotated). Comparing a value with nums[0]
        # says which run it belongs to. The first run is a prefix of the array, the second a
        # suffix.
        first = nums[0]
        target_in_first = target >= first

        # Binary search over the closed range [lo, hi]. The promise kept on every step: if
        # target is in nums, its index is inside [lo, hi].
        lo, hi = 0, len(nums) - 1
        while lo <= hi:
            mid = (lo + hi) // 2  # rounds down; never overflows in Python
            if nums[mid] == target:
                return mid
            mid_in_first = nums[mid] >= first
            if mid_in_first != target_in_first:
                # Different runs: the target's whole run is on one side of mid.
                if target_in_first:
                    hi = mid - 1  # mid is in the second run, and the first run is to its left
                else:
                    lo = mid + 1  # mid is in the first run, and the second run is to its right
            elif nums[mid] < target:
                # Same run, and a run is sorted: an ordinary binary search step.
                lo = mid + 1
            else:
                hi = mid - 1
        return -1  # the range is empty: target isn't in nums
