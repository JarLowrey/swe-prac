import math


class Solution:
    def coinChange(self, coins: list[int], amount: int) -> int:
        # fewest[a] = the fewest coins that add up to exactly a, or infinity if no combination
        # does. Infinity is larger than any real count, so min() and < never pick it over a
        # real answer, and an impossible amount needs no special case until the very end.
        fewest = [0] + [math.inf] * amount  # fewest[0] = 0: paying nothing takes no coins

        # Bottom-up: every amount is built from smaller amounts, which are already final.
        for a in range(1, amount + 1):
            for c in coins:
                # Try c as the last coin: the coins before it pay a - c.
                # c <= a matters: fewest[a - c] with a negative index would quietly read a
                # cell from the end of the list instead of failing.
                if c <= a and fewest[a - c] + 1 < fewest[a]:
                    fewest[a] = fewest[a - c] + 1

        # Convert "impossible" to the -1 the problem asks for only here, at the end.
        return fewest[amount] if fewest[amount] != math.inf else -1
