from collections import Counter


class Solution:
    def topKFrequent(self, nums: list[int], k: int) -> list[int]:
        # Step 1: count each value in one pass (Counter is a dict of value -> count).
        counts = Counter(nums)

        # Step 2: bucket sort by count. A count is a whole number from 1 to len(nums), so
        # buckets[c] can hold the values that appear exactly c times: no comparisons needed.
        buckets: list[list[int]] = [[] for _ in range(len(nums) + 1)]
        for value, count in counts.items():
            buckets[count].append(value)

        # Walk from the highest possible count down, collecting values until there are k.
        top: list[int] = []
        for count in range(len(nums), 0, -1):
            for value in buckets[count]:
                top.append(value)
                if len(top) == k:
                    return top
        return top  # only reached if k is larger than the number of distinct values
