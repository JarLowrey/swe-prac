Given an array `intervals` where `intervals[i] = [start_i, end_i]`, merge every group of
overlapping intervals into one interval. Return the merged intervals: no two of them overlap, and
together they cover exactly the points the input covers.

Two intervals overlap when they share at least one point, so intervals that only touch, such as
`[1, 4]` and `[4, 5]`, merge into `[1, 5]`. The input is in no particular order. Return the
merged intervals in any order.

**Example 1**

```
Input:  intervals = [[1, 3], [2, 6], [8, 10], [15, 18]]
Output: [[1, 6], [8, 10], [15, 18]]
```

`[1, 3]` and `[2, 6]` overlap, so they become `[1, 6]`. The other two overlap nothing.

```intervals
input: [1,3] [2,6] [8,10] [15,18]
merged: [1,6] [8,10] [15,18]
caption: [1,3] and [2,6] share the points 2 to 3, so they merge
```

**Example 2**

```
Input:  intervals = [[1, 4], [4, 5]]
Output: [[1, 5]]
```

The two intervals share the point 4, which counts as overlapping.

**Example 3**

```
Input:  intervals = [[5, 10], [1, 4], [2, 7]]
Output: [[1, 10]]
```

The input isn't sorted. `[1, 4]` and `[5, 10]` don't overlap each other, but both overlap
`[2, 7]`, so all three chain into one interval.

**Constraints**

- `0 <= len(intervals) <= 10^4`
- `intervals[i]` has two elements, and `0 <= start_i <= end_i <= 10^4`.
