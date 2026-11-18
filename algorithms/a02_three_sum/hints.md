**Hint 1.** The brute force tries every triple `i < j < k`, O(n³), and removes repeats by adding
each triplet to a set *sorted*, so `(0, -1, 1)` and `(-1, 0, 1)` become the same key.

**Hint 2.** Fix the first number `a`. You now need two later numbers that add up to `-a`: that's
Two Sum, which takes O(n). Doing it for every `a` is O(n²).

**Hint 3.** Sort the array first. For a fixed `i`, put `lo` just after it and `hi` at the end. If
the sum is too small, only moving `lo` right can raise it; if too big, move `hi` left. Sorting
also puts equal values next to each other, which makes repeats easy to skip.

**Hint 4.** Skip an `i` whose value equals the previous `i`'s value. After recording a triplet,
move `lo` past every copy of its value and `hi` past every copy of its value. Skip only repeated
*first* values, never the copies the pair search uses: `[-3, -3, 6]` needs both -3s.
