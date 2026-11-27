**Hint 1.** The brute force decides, for each element, to take it or skip it: 2^n subsequences.
When you decide about `nums[i]`, what do you need to know about the choices made so far? (Only
the last element you took.)

**Hint 2.** Ask a different question per index: "what is the longest increasing subsequence that
ends exactly at `nums[i]`?" Its previous element is some `nums[j]` with `j < i` and
`nums[j] < nums[i]`, so `ending[i] = 1 + max(ending[j])` over those `j`, or 1 if there are none.

**Hint 3.** That's O(n²). The answer is `max(ending)`, not `ending[-1]`: the longest subsequence
can end anywhere.

**Hint 4.** For O(n log n), keep `tails[k]`: the smallest value that can end an increasing
subsequence of length `k + 1`. `tails` is sorted, so for each `x` binary search for the first
tail `>= x` (`bisect_left`) and replace it with `x`, or append `x` if every tail is smaller. The
answer is `len(tails)`.
