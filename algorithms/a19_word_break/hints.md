**Hint 1.** Some prefix `s[:j]` must be the first word. You don't know which one, so try every
prefix that is a word and ask the same question about the rest, `s[j:]`. Picking the longest or
the shortest word greedily fails (try `"goalspecial"` with `["go", "goal", "goals", "special"]`).

**Hint 2.** The rest of the string is always a suffix, so the whole state is one index `i`: "can
`s[i:]` be split?" An empty rest (`i == len(s)`) is a complete split: return `True` there.

**Hint 3.** The plain recursion asks about the same suffix over and over: `"aaaa...ab"` with
`["a", "aa", "aaa"]` takes exponential time and then fails. Memoize on `i` (an index, not the
substring), and store the `False` answers too. Put the words in a set.

**Hint 4.** Bottom-up: `ok[n] = True`, then for `i` from `n - 1` down to 0, `ok[i]` is `True`
when some word `s[i:j]` is followed by a `j` with `ok[j] == True`. Only word lengths up to the
longest word need checking.
