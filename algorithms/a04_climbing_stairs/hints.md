**Hint 1.** Think about the very last move. Standing on step `n`, where could you have been just
before it?

**Hint 2.** You came from step `n - 1` (a 1-step) or from step `n - 2` (a 2-step). Those two
groups of ways never overlap, because their last moves differ, so
`ways(n) = ways(n - 1) + ways(n - 2)`. For the base cases, `ways(1) = 1`, and `ways(0) = 1`:
standing at the top already is one complete way.

**Hint 3.** Written as plain recursion, this recomputes the same values again and again:
`ways(n - 2)` is computed by `ways(n)` and again inside `ways(n - 1)`, and the calls double at
every level. There are only `n + 1` different questions, so store each answer (a memo keyed by
`n`), or fill an array from step 0 upwards.

**Hint 4.** Each value needs only the two before it, so two variables are enough: O(n) time and
O(1) space. The answers 1, 2, 3, 5, 8, ... are the Fibonacci numbers.
