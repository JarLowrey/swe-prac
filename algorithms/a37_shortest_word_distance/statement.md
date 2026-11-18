Given a list of words `wordsDict` and two different words `word1` and `word2` that both appear in
it, return the shortest distance between an occurrence of `word1` and an occurrence of `word2`.

The distance between the words at indices `i` and `j` is `|i - j|`, so neighbouring words are 1
apart. Either word may come first, and both may appear many times.

**Example 1**

```
Input:  wordsDict = ["the", "quick", "brown", "fox", "quick"], word1 = "the", word2 = "fox"
Output: 3
```

`"the"` is at index 0 and `"fox"` at index 3.

**Example 2**

```
Input:  wordsDict = ["the", "quick", "brown", "fox", "quick"], word1 = "quick", word2 = "fox"
Output: 1
```

The first `"quick"` is 2 away from `"fox"`, but the second one is next to it.

```array
label: wordsDict
values: the quick brown fox quick
highlight: 3 4
caption: "fox" at 3 and "quick" at 4: distance 1
```

**Example 3**

```
Input:  wordsDict = ["a", "b", "c", "d", "c", "a"], word1 = "a", word2 = "c"
Output: 1
```

The closest pair is at the end: `"c"` at index 4 and `"a"` at index 5.

**Constraints**

- `2 <= len(wordsDict) <= 3 × 10^4`
- Each word has 1 to 10 lowercase English letters.
- `word1` and `word2` are both in `wordsDict`, and `word1 != word2`.
