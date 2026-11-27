class Solution:
    def merge(self, intervals: list[list[int]]) -> list[list[int]]:
        # Sorted by start, the intervals that merge together sit next to each other, so a single
        # left-to-right pass can merge them.
        merged: list[list[int]] = []
        for start, end in sorted(intervals, key=lambda iv: iv[0]):
            if merged and start <= merged[-1][1]:
                # It overlaps or touches the last merged interval: extend that interval. Take the
                # max: an interval nested inside the last one must not shorten it. The start never
                # changes, since nothing later starts earlier.
                merged[-1][1] = max(merged[-1][1], end)
            else:
                # A gap: every later interval starts at `start` or after, so none can reach back
                # into the last merged interval. Start a new one. Append a copy, so extending it
                # never modifies the caller's lists.
                merged.append([start, end])
        return merged
