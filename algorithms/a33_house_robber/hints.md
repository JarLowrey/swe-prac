**Hint 1.** Robbing every other house (all the even indexes, or all the odd ones) isn't always
best: try `[2, 1, 1, 2]`. Neither is "take the richest house, then the richest one left": try
`[2, 3, 2]`.

**Hint 2.** At each house you choose: rob it, and then the next house is off limits, or skip it.
If `best(i)` is the most you can take from houses `i` to the end, then
`best(i) = max(nums[i] + best(i + 2), best(i + 1))`, and `best(i) = 0` once `i` is past the last
house.

**Hint 3.** The plain recursion solves the same `best(i)` many times: robbing house 0 and skipping
houses 0 and 1 both arrive at house 2. Memoize on `i`, or fill the values from the last house
back to the first.

**Hint 4.** Each value only needs the next two, so two variables are enough: O(n) time and O(1)
space.
