**Hint 1.** The brute force collects the positions of each word and tries every pair: O(n²) when
both words are common. Do you really need to compare an occurrence with *every* occurrence of the
other word?

**Hint 2.** Suppose `word1` is at `i` and `word2` at `j`, and another copy of either word sits
between them. Then that copy and one of the two ends form a closer pair. So the closest pair has
no occurrence of either word between them.

**Hint 3.** Walk the list once and remember only the index of the most recent `word1` or `word2`.
Which single number from the past does the current word need?

**Hint 4.** At each occurrence, if the most recent occurrence was the *other* word, `i - last` is
a candidate. Then set `last = i` either way: a newer copy is always at least as close to anything
still to come. Start with `last = -1` and check it before reading `wordsDict[last]` (in Python,
`wordsDict[-1]` is the last word, not an error).
