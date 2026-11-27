Given an integer array `nums` and an integer `k`, return the `k` values that appear most often in
`nums`. Return them in any order.

The answer is always unique: the `k`-th most frequent value appears strictly more often than any
value left out.

**Example 1**

```
Input:  nums = [1, 1, 1, 2, 2, 3], k = 2
Output: [1, 2]
```

1 appears three times, 2 twice and 3 once. The two most frequent values are 1 and 2.

```grid
rowlabels: value count
1 2 3
3 2 1
highlight: 0,0 1,0 0,1 1,1
caption: the counts for Example 1: the top 2 are 1 and 2
```

**Example 2**

```
Input:  nums = [1], k = 1
Output: [1]
```

**Example 3**

```
Input:  nums = [4, 1, -1, 2, -1, 2, 3], k = 2
Output: [-1, 2]
```

-1 and 2 appear twice each; every other value appears once. `[2, -1]` is also accepted.

**Constraints**

- `1 <= len(nums) <= 10^5`
- `-10^4 <= nums[i] <= 10^4`
- `1 <= k <=` the number of distinct values in `nums`
- The answer is unique.

**Follow-up:** sorting gives O(n log n). Can you do better?
