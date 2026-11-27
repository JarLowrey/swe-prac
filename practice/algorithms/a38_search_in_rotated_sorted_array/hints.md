**Hint 1.** A scan is O(n). O(log n) means binary search: every step must rule out half of the
range that's left. Try plain binary search on Example 1 by hand. Where does it go wrong?

**Hint 2.** The array is two sorted runs: first the larger values, then the smaller ones. Every
value in the first run is at least `nums[0]`, and every value in the second run is smaller than
`nums[0]`. So comparing a value with `nums[0]` tells you which run it is in.

**Hint 3.** Classify both `nums[mid]` and `target` that way. If they are in the same run, that
run is sorted, so an ordinary binary search step is safe. If they are in different runs, you
already know which side of `mid` the target's run lies on.

**Hint 4.** If `target >= nums[0]` but `nums[mid] < nums[0]`, the target can only be left of
`mid`: set `hi = mid - 1`. In the opposite case, set `lo = mid + 1`. Loop while `lo <= hi` and
return `-1` once the range is empty.
