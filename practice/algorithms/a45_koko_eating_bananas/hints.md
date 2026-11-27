**Hint 1.** Fix a speed `k`. How many hours does Koko need? A pile of `p` bananas takes `p / k`
hours rounded up, so checking one speed is a single pass over the piles.

**Hint 2.** Which speeds can be the answer? At speed `max(piles)` every pile takes one hour, which
always fits, and faster speeds can't do better. So the answer is in `1..max(piles)`. Trying the
speeds from 1 upwards is correct, but `max(piles)` can be a billion.

**Hint 3.** If speed `k` is fast enough, so is every faster speed. Down the list of speeds,
"fast enough?" reads no, no, ..., no, yes, yes, ..., yes, and you want the first yes. Binary
search the speeds, not the piles.

**Hint 4.** Start with `lo, hi = 1, max(piles)`. While `lo < hi`, take `mid = (lo + hi) // 2`. If
`mid` is fast enough, the answer is `mid` or slower (`hi = mid`); otherwise it is faster
(`lo = mid + 1`). When the loop ends, `lo` is the answer.
