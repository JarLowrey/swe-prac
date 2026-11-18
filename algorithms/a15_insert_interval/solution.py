class Solution:
    def insert(self, intervals: list[list[int]], newInterval: list[int]) -> list[list[int]]:
        # The list is sorted and overlap-free, so the intervals before newInterval, the ones
        # overlapping it and the ones after it form three runs in that order. One index walks
        # through them: O(n), no sorting.
        out: list[list[int]] = []
        i, n = 0, len(intervals)
        start, end = newInterval  # the merged interval, in locals: the input isn't modified

        # 1. Before: ends before the new interval starts (strictly: touching means merging).
        while i < n and intervals[i][1] < start:
            out.append(intervals[i])
            i += 1

        # 2. Overlapping: starts at or before the merged interval ends. Absorb it.
        while i < n and intervals[i][0] <= end:
            start = min(start, intervals[i][0])
            end = max(end, intervals[i][1])
            i += 1
        out.append([start, end])  # appended even when nothing overlapped

        # 3. After: starts after the merged interval ends. The input's intervals don't touch,
        # so none of these can overlap it, even though its end may have grown.
        out.extend(intervals[i:])
        return out
