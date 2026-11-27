class Solution:
    def containsDuplicate(self, nums: list[int]) -> bool:
        # Every value met so far. "Have I seen x?" is an O(1) lookup in a set (on average),
        # which replaces the brute force's scan of the rest of the array.
        seen: set[int] = set()
        for x in nums:
            if x in seen:
                return True  # the second copy of x: stop at the first repeat
            seen.add(x)
        # Every lookup missed, so each value was new when we met it: all are distinct.
        return False
