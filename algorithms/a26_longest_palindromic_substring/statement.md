Given a string `s`, return its longest substring that is a palindrome. A palindrome reads the
same forwards and backwards. A substring is a contiguous run of characters: you can't skip or
rearrange any.

If several palindromes share the longest length, return any one of them.

**Example 1**

```
Input:  s = "baba"
Output: "bab"
```

`"aba"` is also accepted: both have length 3, and `"baba"` itself is not a palindrome.

```array
label: s
values: b a b a
highlight: 0..2
caption: "bab" reads the same both ways; so does "aba"
```

**Example 2**

```
Input:  s = "babab"
Output: "babab"
```

The whole string is a palindrome.

**Example 3**

```
Input:  s = "cbbd"
Output: "bb"
```

A palindrome can have an even length. Its middle is then the gap between two characters.

**Constraints**

- `1 <= len(s) <= 2500`
- `s` consists of English letters and digits. Upper and lower case letters are different
  characters.

**Follow-up:** checking every substring is O(n³). Can you do it in O(n²) time and O(1) extra
space?
