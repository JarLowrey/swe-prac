You are climbing a staircase with `n` steps. Each move climbs either 1 step or 2 steps. In how
many distinct ways can you reach the top?

Two ways are different when their sequences of moves are different: `1 + 2` and `2 + 1` count as
two ways.

**Example 1**

```
Input:  n = 2
Output: 2
```

`1 + 1`, or a single `2`.

**Example 2**

```
Input:  n = 3
Output: 3
```

`1 + 1 + 1`, `1 + 2` or `2 + 1`. Each way lands on a different set of stairs:

```array
label: stair
values: 0 1 2 3
indices: false
highlight: 0 1 2 3
caption: 1 + 1 + 1: land on every stair
---
label: stair
values: 0 1 2 3
indices: false
highlight: 0 1 3
dim: 2
caption: 1 + 2: land on stair 1, then jump over stair 2
---
label: stair
values: 0 1 2 3
indices: false
highlight: 0 2 3
dim: 1
caption: 2 + 1: jump over stair 1, then step up to 3
```

**Example 3**

```
Input:  n = 4
Output: 5
```

`1 + 1 + 1 + 1`, `1 + 1 + 2`, `1 + 2 + 1`, `2 + 1 + 1` and `2 + 2`.

**Constraints**

- `1 <= n <= 45` (the answer fits in a 32-bit signed integer)

**Follow-up:** can you do it in O(n) time and O(1) extra space?
