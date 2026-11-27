Given an array `intervals` where `intervals[i] = [start_i, end_i]`, return the minimum number of
intervals you need to remove so that the remaining intervals don't overlap.

Intervals that only touch do **not** overlap here: think of meetings, where one can end at 2 and
the next start at 2. So `[1, 2]` and `[2, 3]` can both stay, but `[1, 3]` and `[2, 4]` can't.

**Example 1**

```
Input:  intervals = [[1, 3], [2, 5], [4, 6]]
Output: 1
```

`[2, 5]` overlaps both of the others. Removing it leaves `[1, 3]` and `[4, 6]`, which don't
overlap.

```intervals
input: [1,3] [2,5] [4,6]
kept: [1,3] [4,6]
caption: remove [2,5] and the rest fit side by side
```

**Example 2**

```
Input:  intervals = [[1, 2], [1, 2], [1, 2]]
Output: 2
```

Only one copy of `[1, 2]` can stay.

**Example 3**

```
Input:  intervals = [[1, 2], [2, 3]]
Output: 0
```

They touch at 2, which isn't an overlap.

**Constraints**

- `0 <= len(intervals) <= 10^4`
- `-5 * 10^4 <= start_i < end_i <= 5 * 10^4`
