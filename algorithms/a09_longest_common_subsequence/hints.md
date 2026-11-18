**Hint 1.** Compare the first characters of the two strings. If they're equal, is it ever wrong
to match them with each other? If they're different, at least one of the two can't be part of
the answer. Which one?

**Hint 2.** You can't know which, so try both and keep the better: with `i` and `j` marking where
the rest of each string starts, `lcs(i, j) = 1 + lcs(i + 1, j + 1)` when
`text1[i] == text2[j]`, otherwise `max(lcs(i + 1, j), lcs(i, j + 1))`. When either string is used
up, the answer is 0.

**Hint 3.** Only the pair `(i, j)` changes, so there are at most
`(len(text1) + 1) × (len(text2) + 1)` different subproblems, but the plain recursion solves
them exponentially many times. Memoize on `(i, j)`,
and pass indexes rather than slicing the strings (each slice copies).

**Hint 4.** Bottom-up: a table `dp[i][j]` for the suffixes `text1[i:]` and `text2[j:]`, filled
from the bottom-right corner, where the last row and column (an empty suffix) are 0. Each row only
reads the row below it, so two rows are enough.
