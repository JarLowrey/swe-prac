Given a string `s` made only of the characters `(`, `)`, `[`, `]`, `{` and `}`, return whether it
is valid. A string is valid when:

- every closing bracket closes an open bracket of the same type,
- brackets close in the right order: the most recently opened bracket closes first,
- every open bracket is closed by the end of the string.

An empty string is valid.

**Example 1**

```
Input:  s = "()[]{}"
Output: True
```

Three pairs, one after another.

**Example 2**

```
Input:  s = "{[()]}"
Output: True
```

Nested pairs: each closing bracket matches the innermost bracket still open.

**Example 3**

```
Input:  s = "(]"
Output: False
```

`]` can't close `(`.

**Example 4**

```
Input:  s = "([)]"
Output: False
```

The counts balance, but `)` arrives while `[` is the innermost open bracket.

```array
label: s
values: ( [ ) ]
highlight: 1 2
caption: ")" must close the most recent open bracket, which is "["
```

**Constraints**

- `0 <= len(s) <= 10^5`
- `s` contains only `()[]{}`.
