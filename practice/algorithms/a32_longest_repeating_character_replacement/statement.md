You are given a string `s` of uppercase English letters and an integer `k`. You may change any
character of `s` into any other uppercase letter, at most `k` times in total.

Return the length of the longest substring that can be made of one repeated letter using at most
`k` changes.

**Example 1**

```
Input:  s = "ABAB", k = 2
Output: 4
```

Change both `A`s into `B`s (or both `B`s into `A`s): the whole string becomes one letter.

**Example 2**

```
Input:  s = "EEBAA", k = 1
Output: 3
```

Change the `B` in `"EEB"` to get `"EEE"`, or in `"BAA"` to get `"AAA"`. A substring of length
4, such as `"EEBA"`, would need two changes.

```array
label: s
values: E E B A A
highlight: 0..2
caption: "EEB": change the B and it reads "EEE"
```

**Example 3**

```
Input:  s = "EEBEE", k = 1
Output: 5
```

One change bridges the gap: `"EEEEE"`.

**Constraints**

- `1 <= len(s) <= 10^5`
- `s` consists of uppercase English letters.
- `0 <= k <= len(s)`
