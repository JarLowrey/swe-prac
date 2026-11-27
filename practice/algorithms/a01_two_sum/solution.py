class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        # Every element to the left of i, by value. Looking a value up is O(1) on average,
        # which replaces the brute force's inner loop.
        seen: dict[int, int] = {}
        for i, x in enumerate(nums):
            need = target - x  # the only value that completes a pair with x
            if need in seen:
                # seen holds only earlier elements, so this is never x paired with itself.
                return [seen[need], i]
            seen[x] = i  # record x after the lookup, for the elements still to come
        return []  # not reached: every input has exactly one answer
