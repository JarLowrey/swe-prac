**Hint 1.** Start with the brute force: compare every pair `i < j`. It is correct, and it shows
where the time goes: for each element you scan the rest of the array for one specific value.

**Hint 2.** If the array were sorted, where would two equal values be? That gives an
O(n log n) solution.

**Hint 3.** For O(n), ask each element a different question: not "does this value appear
later?" but "have I already seen this value?" Which data structure answers that in O(1)?

**Hint 4.** Walk the array once with a set. If the current value is already in the set, return
`True`; otherwise add it. If the loop finishes, every value was new, so return `False`.
