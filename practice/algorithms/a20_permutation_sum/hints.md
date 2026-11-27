**Hint 1.** Don't build the sequences: there can be two billion of them. Count instead. If the
first number of a sequence is `x`, the rest is any sequence that adds up to `target - x`.

**Hint 2.** So `count(t)` is the sum of `count(t - x)` over the numbers `x <= t`, and
`count(0) = 1`: when nothing is left, the sequence is complete, and that is one way. A number
bigger than what's left would overshoot, so it contributes nothing.

**Hint 3.** `count(t)` depends only on `t`, and the same remainders come up again and again:
taking 1 then 2, or 2 then 1, both leave `4 - 3 = 1`. Memoize on the remaining target, or fill
`ways[0..target]` from 0 upwards. Store zeros in the memo too.

**Hint 4.** Loop over the target on the outside and over `nums` on the inside. Swapping the loops
counts each combination only once, ignoring order: that's a different problem.
