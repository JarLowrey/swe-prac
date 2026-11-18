class Solution:
    def eraseOverlapIntervals(self, intervals: list[list[int]]) -> int:
        # Fewest removals = most intervals kept. Go in order of start, and whenever an interval
        # overlaps the one we're keeping, keep whichever of the two ends first.
        removed = 0
        prev_end = float("-inf")  # end of the last kept interval; nothing kept yet
        for start, end in sorted(intervals, key=lambda iv: iv[0]):
            if start < prev_end:
                # Overlap (strict: an interval starting exactly at prev_end only touches). One
                # of the two must go. Everything later starts at or after both, so only the end
                # matters for the future, and the earlier end leaves the most room.
                removed += 1
                prev_end = min(prev_end, end)
            else:
                prev_end = end  # no overlap: keep it
        return removed
