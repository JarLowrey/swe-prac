Given two strings `s` and `t`, return the shortest substring of `s` that contains every
character of `t`, **including duplicates**: if `t` has two `a`s, the substring needs at least two
`a`s. The order of the characters doesn't matter, and the substring may contain other characters
too.

If no substring of `s` contains all of `t`, return the empty string `""`. The tests are built so
that the shortest substring, when there is one, is unique.

**Example 1**

```
Input:  s = "aebc", t = "abc"
Output: "aebc"
```

The `a` is at the start and the `c` at the end, so only the whole string contains all three.

**Example 2**

```
Input:  s = "aetbxab", t = "ab"
Output: "ab"
```

`"aetb"` is the first substring that contains an `a` and a `b`, but `"bxa"` and then `"ab"`
are shorter.

```array
label: s
values: a e t b x a b
highlight: 5 6
caption: "aetb" (length 4) and "bxa" (3) also contain a and b; "ab" is shortest
```

**Example 3**

```
Input:  s = "acbbaca", t = "aba"
Output: "baca"
```

`t` needs two `a`s and one `b`. `"acb"` has only one `a`.

**Example 4**

```
Input:  s = "a", t = "aa"
Output: ""
```

`s` has only one `a`, so no substring contains `t`.

**Constraints**

- `1 <= len(s), len(t) <= 10^5`
- `s` and `t` consist of English letters. Upper and lower case letters are different
  characters.
- The shortest substring containing `t` is unique when one exists.

**Follow-up:** can you do it in O(len(s) + len(t)) time?
