**Hint 1.** Draw the intervals on a number line. Two intervals `a` and `b` overlap when each
starts no later than the other ends: `a[0] <= b[1] and b[0] <= a[1]`. Comparing every pair is
O(n²), and it isn't even enough on its own: merging two intervals can make a new interval that
overlaps a third.

**Hint 2.** In what order would the intervals that belong together end up next to each other?
Try sorting by start.

**Hint 3.** After sorting by start, walk the intervals and keep the last merged interval. The
next interval either starts at or before its end (it overlaps: extend the end), or after it (a
gap: no later interval can reach back across it, so start a new merged interval).

**Hint 4.** Extend with `max(last_end, end)`, not just `end`: a short interval nested inside a
long one must not cut it short. And append a copy (`[start, end]`) rather than the input's own
list, so you never change the caller's data when you extend it.
