class Solution:
    def pairSum(self, nums: list[int], target: int) -> list[int]:
        seen: dict[int, int] = {}  # value -> index, for everything left of i
        for i, x in enumerate(nums):
            if target - x in seen:
                return [seen[target - x], i]
            seen[x] = i
        return []
