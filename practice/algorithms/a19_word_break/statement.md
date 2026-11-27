Given a string `s` and a list of words `wordDict`, return `True` if `s` can be split into a
sequence of one or more dictionary words, with nothing left over, and `False` otherwise.

The same word may be used any number of times.

**Example 1**

```
Input:  s = "yellowsun", wordDict = ["yell", "yellow", "sun"]
Output: True
```

`"yellow" + "sun"`. Starting with `"yell"` leaves `"owsun"`, which can't be split, so the first
word that fits isn't always the right one.

```array
label: s
values: y e l l o w s u n
highlight: 0..5
caption: "yellow" is a word...
---
label: s
values: y e l l o w s u n
dim: 0..5
highlight: 6..8
caption: ...and so is the rest, "sun"
```

**Example 2**

```
Input:  s = "applepenapple", wordDict = ["apple", "pen"]
Output: True
```

`"apple" + "pen" + "apple"`: a word can be used again.

**Example 3**

```
Input:  s = "catsandog", wordDict = ["cats", "dog", "sand", "and", "cat"]
Output: False
```

`"cats" + "and"` and `"cat" + "sand"` both leave `"og"`, which isn't a word.

**Constraints**

- `1 <= len(s) <= 300`
- `1 <= len(wordDict) <= 1000`
- `1 <= len(wordDict[i]) <= 20`
- `s` and the words contain only lowercase English letters, and the words are all different.
