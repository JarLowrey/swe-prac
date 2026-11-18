Given two strings `s` and `t`, return `True` if `t` is an anagram of `s`, and `False` otherwise.

An anagram uses exactly the same letters, each exactly as many times, possibly in a different
order.

**Example 1**

```
Input:  s = "anagram", t = "nagaram"
Output: True
```

Both strings have three a's and one each of g, m, n and r.

```grid
collabels: a g m n r
rowlabels: s t
3 1 1 1 1
3 1 1 1 1
caption: letter counts: every column matches
```

**Example 2**

```
Input:  s = "rat", t = "car"
Output: False
```

`t` has a c and no t.

**Example 3**

```
Input:  s = "tea", t = "eat"
Output: True
```

**Constraints**

- `0 <= len(s), len(t) <= 5 × 10^4`
- `s` and `t` consist of lowercase English letters.

**Follow-up:** what would you change if the strings could contain any Unicode characters?
