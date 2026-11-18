class Solution:
    def maxProfit(self, prices: list[int]) -> int:
        # The best trade that sells on day j buys at the cheapest price on or before day j, so one
        # pass only needs two running numbers instead of comparing every pair of days.
        lowest = float("inf")  # cheapest price so far; infinity also handles an empty array
        best = 0  # not trading is always allowed, so the answer is never negative
        for price in prices:
            # On a new low this "buys and sells" the same day for 0, which is harmless.
            lowest = min(lowest, price)
            best = max(best, price - lowest)  # the best trade that sells today
        return best
