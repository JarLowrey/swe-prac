**Hint 1.** Try "always take the biggest coin that fits" on `coins = [1, 3, 4]`, `amount = 6`,
and on `coins = [2, 5]`, `amount = 6`. If the biggest coin can be the wrong choice, what's left
but trying every coin?

**Hint 2.** If the first coin you use is `c`, what remains is the same problem for `amount - c`.
So `fewest(a) = 1 + min(fewest(a - c))` over the coins `c <= a`, with `fewest(0) = 0`. When no
coin works, the amount is impossible: use infinity, which never wins a `min`.

**Hint 3.** The same remaining amounts come up again and again along different paths
(6 - 1 - 3 and 6 - 3 - 1 both leave 2). The answer depends only on the amount left, so memoize
on it, and remember to store the impossible amounts too.

**Hint 4.** Bottom-up: `dp[0] = 0`, then for `a = 1..amount`,
`dp[a] = 1 + min(dp[a - c] for c in coins if c <= a)`. Return `dp[amount]`, or `-1` if it's still
infinity. That's O(len(coins) × amount) time and O(amount) space.
