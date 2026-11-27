A message of capital letters is encoded as digits, with `A` as `"1"`, `B` as `"2"`, and so on up
to `Z` as `"26"`. To decode a string of digits, split it into groups and turn each group back
into a letter. Some letters take two digits, so one string can often be split in several ways.

Given a string `s` of digits, return the number of ways to decode it. Every group must be exactly
the code of a letter, `"1"` to `"26"`: a group can't start with 0 (`"06"` is not `F`), and `"0"`
on its own is not a letter. If `s` can't be decoded at all, return 0.

**Example 1**

```
Input:  s = "12"
Output: 2
```

`1 2` is `AB`, and `12` is `L`.

**Example 2**

```
Input:  s = "226"
Output: 3
```

```array
label: groups
values: 2 2 6
indices: false
caption: 2 2 6 is B B F
---
label: groups
values: 22 6
indices: false
caption: 22 6 is V F
---
label: groups
values: 2 26
indices: false
caption: 2 26 is B Z
```

**Example 3**

```
Input:  s = "106"
Output: 1
```

Only `10 6` (`JF`) works: `1 06` would need a group with a leading zero.

**Example 4**

```
Input:  s = "06"
Output: 0
```

`"06"` is not a code, and `"0"` on its own isn't either, so nothing can decode the first digit.

**Constraints**

- `1 <= len(s) <= 100`
- `s` contains only digits, and may start with `0`.
- The answer fits in a 32-bit signed integer.
