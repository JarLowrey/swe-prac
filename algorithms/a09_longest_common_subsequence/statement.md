Given two strings `text1` and `text2`, return the length of their longest common subsequence, or
`0` if they have none.

A subsequence of a string keeps some of its characters (possibly none, possibly all) in their
original order: `"ace"` is a subsequence of `"abcde"`, but `"aec"` is not. A common subsequence is
a subsequence of both strings.

**Example 1**

```
Input:  text1 = "abcde", text2 = "ace"
Output: 3
```

`"ace"` is a subsequence of both strings.

```array
label: text1
values: a b c d e
highlight: 0 2 4
---
label: text2
values: a c e
highlight: 0 1 2
caption: the highlighted letters spell "ace" in both strings, in the same order
```

**Example 2**

```
Input:  text1 = "abc", text2 = "abc"
Output: 3
```

A string is a subsequence of itself.

**Example 3**

```
Input:  text1 = "abc", text2 = "def"
Output: 0
```

No letter appears in both strings.

**Constraints**

- `1 <= len(text1), len(text2) <= 1000`
- Both strings contain only lowercase English letters.
