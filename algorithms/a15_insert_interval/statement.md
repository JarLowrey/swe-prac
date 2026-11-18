You are given `intervals`, a list of intervals `[start_i, end_i]` that don't overlap and are sorted
by start, and one more interval, `newInterval = [start, end]`.

Insert `newInterval` so that the list is still sorted by start and still has no overlapping
intervals, merging intervals where you need to. Return the resulting list. You may build a new
list rather than changing `intervals`.

Intervals that share a point overlap, including ones that only touch: `[1, 3]` and `[3, 5]`
merge into `[1, 5]`.

**Example 1**

```
Input:  intervals = [[1, 3], [6, 9]], newInterval = [2, 5]
Output: [[1, 5], [6, 9]]
```

`[2, 5]` overlaps `[1, 3]`, so the two become `[1, 5]`.

**Example 2**

```
Input:  intervals = [[1, 2], [3, 5], [6, 7], [8, 10], [12, 16]], newInterval = [4, 8]
Output: [[1, 2], [3, 10], [12, 16]]
```

`[4, 8]` overlaps `[3, 5]` and `[6, 7]`, and touches `[8, 10]`, so all four merge into
`[3, 10]`.

```intervals
intervals: [1,2] [3,5] [6,7] [8,10] [12,16]
new: [4,8]
result: [1,2] [3,10] [12,16]
```

**Example 3**

```
Input:  intervals = [[0, 1], [2, 3], [4, 5], [6, 7]], newInterval = [2, 4]
Output: [[0, 1], [2, 5], [6, 7]]
```

`[2, 4]` overlaps `[2, 3]` and touches `[4, 5]`. `[6, 7]` starts after 5, so it stays separate.

**Constraints**

- `0 <= len(intervals) <= 10^4`
- `0 <= start_i <= end_i <= 10^5`
- `intervals` is sorted by start, and no two intervals overlap or touch: `end_i < start_(i+1)`.
- `newInterval = [start, end]` with `0 <= start <= end <= 10^5`.

**Follow-up:** appending `newInterval` and re-sorting is O(n log n). Can you do it in O(n)?
