**Hint 1.** Start with the brute force: try every pair `i < j`. It is correct, and it tells you
what is slow: for each number you scan the whole array again.

**Hint 2.** For a number `x`, you know exactly which value would complete the pair: `target - x`.
The question for each element is just "have I seen `target - x` already?"

**Hint 3.** Which data structure answers "have I seen this value, and where?" in O(1)?

**Hint 4.** Walk the array once with a dict from value to index. For each `x`, look up
`target - x` *before* storing `x`, so an element is never paired with itself.
