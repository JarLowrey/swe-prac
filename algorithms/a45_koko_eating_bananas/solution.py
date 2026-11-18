class Solution:
    def minEatingSpeed(self, piles: list[int], h: int) -> int:
        # Binary search over the answer (the speed), not over the piles. Every speed below the
        # answer is too slow and every speed from the answer up fits, so we look for the boundary.
        # The answer is always inside [lo, hi]: no speed is below 1, and at speed max(piles)
        # each pile takes one hour, which fits because there are at most h piles.
        lo, hi = 1, max(piles)
        while lo < hi:
            mid = (lo + hi) // 2  # rounds down, so mid < hi and the range always shrinks
            if self.hours_needed(piles, mid) <= h:
                hi = mid  # mid is fast enough: the answer is mid or slower (keep mid)
            else:
                lo = mid + 1  # mid is too slow: the answer is faster
        return lo  # lo == hi: the slowest speed that fits

    def hours_needed(self, piles: list[int], k: int) -> int:
        # A pile of p bananas takes ceil(p / k) hours: a part-eaten last hour still counts.
        # (p + k - 1) // k is that ceiling in exact integer arithmetic, with no float division.
        return sum((p + k - 1) // k for p in piles)
