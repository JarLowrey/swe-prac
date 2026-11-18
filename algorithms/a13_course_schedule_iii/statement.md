There are `n` online courses. `courses[i] = [duration_i, lastDay_i]` means course `i` takes
`duration_i` days in a row and must be finished on or before day `lastDay_i`.

You start on day 1 and take one course at a time: each course starts the day after the previous
one finishes. So if you take courses with durations `d1, d2, ...` in that order, the first
finishes on day `d1`, the second on day `d1 + d2`, and so on. Each must finish no later than its
own `lastDay`.

Return the maximum number of courses you can take.

**Example 1**

```
Input:  courses = [[100, 200], [200, 1300], [1000, 1250], [2000, 3200]]
Output: 3
```

Take course 0 (days 1 to 100), then course 2 (days 101 to 1100), then course 1 (days 1101 to
1300). Each finishes on time. Course 3 would then finish on day 3300, after its last day, 3200.

```intervals
course 0, due 200: [0,100]
course 2, due 1250: [100,1100]
course 1, due 1300: [1100,1300]
caption: the bars show days used: course 1 finishes on day 1300, exactly its last day
```

**Example 2**

```
Input:  courses = [[1, 2]]
Output: 1
```

**Example 3**

```
Input:  courses = [[3, 2], [4, 3]]
Output: 0
```

Each course takes longer than the time before its last day, even on its own.

**Example 4**

```
Input:  courses = [[1, 2], [5, 6]]
Output: 2
```

Take the short course on day 1, then the long one on days 2 to 6. Finishing on the last day
itself is allowed.

**Constraints**

- `1 <= len(courses) <= 10^4`
- `1 <= duration_i, lastDay_i <= 10^4`
