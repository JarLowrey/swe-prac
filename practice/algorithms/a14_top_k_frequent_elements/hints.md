**Hint 1.** Split the problem in two: count how often each value appears (a hash map, one pass),
then pick the `k` values with the largest counts.

**Hint 2.** Sorting the distinct values by count works: O(n log n) in the worst case. Beware of
`sorted(set(nums), key=nums.count)`: `nums.count` rescans the whole array for every value, which
is O(n²).

**Hint 3.** To beat a full sort, keep only the best `k` seen so far in a **min**-heap ordered by
count. The root is the weakest of the `k`; when the heap grows past `k`, pop it. That's
O(n log k).

**Hint 4.** For O(n): a count is a whole number from 1 to `n`. Put each value in a bucket indexed by
its count, then walk the buckets from `n` down to 1, collecting values until you have `k`.
