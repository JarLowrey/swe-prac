**Hint 1.** Peel off the first group: it's one digit or two. Each valid choice leaves a shorter
string to decode in the same way, and the two choices give different decodings, so their counts
add up.

**Hint 2.** When is a group valid? One digit: anything but `"0"`. Two digits: from `"10"` to
`"26"`, which already rules out a leading zero. So a `0` can only ever be the second digit of
`"10"` or `"20"`; a position that starts with `0` has 0 ways.

**Hint 3.** Describe the rest by its start index: `ways(i)` decodes `s[i:]`, and
`ways(len(s)) = 1` (nothing left is one complete decoding). The plain recursion is exponential on
`"1111..."` (it's the Fibonacci numbers), so memoize on `i`.

**Hint 4.** Bottom-up from the end: `dp[n] = 1`, then for `i` from `n - 1` down to 0, `dp[i]`
is 0 if `s[i] == "0"`. Otherwise it is `dp[i + 1]`, plus `dp[i + 2]` when `i + 1 < n` and
`"10" <= s[i:i + 2] <= "26"`. Each value needs only the next two, so two variables are enough.
