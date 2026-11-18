Given a string `s`, return the length of the longest substring of `s` in which no character
appears twice. A substring is a contiguous run of characters.

**Example 1**

```
Input:  s = "abcda"
Output: 4
```

`"abcd"` and `"bcda"` both have four different characters; all five would repeat the `a`.

```array
label: s
values: a b c d a
highlight: 0..3
caption: "abcd": four characters, no repeats
```

**Example 2**

```
Input:  s = "bbbb"
Output: 1
```

Any substring longer than one character repeats `b`.

**Example 3**

```
Input:  s = "pwwkew"
Output: 3
```

`"wke"` is the longest. `"pwke"` has no repeats, but it isn't contiguous in `s`: it skips a `w`.

**Constraints**

- `0 <= len(s) <= 5 × 10^4`
- `s` consists of English letters, digits, symbols and spaces (printable ASCII). Upper and lower
  case letters are different characters.
