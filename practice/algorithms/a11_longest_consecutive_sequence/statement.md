Given an unsorted array of integers `nums`, return the length of the longest run of consecutive
integers `x, x + 1, x + 2, ...` whose values all appear in `nums`.

The values can sit anywhere in the array, in any order, and a value that appears several times
counts once.

**Example 1**

```
Input:  nums = [100, 4, 200, 1, 3, 2]
Output: 4
```

The values 1, 2, 3 and 4 are all present. 100 and 200 are runs of length 1.

```array
values: _ 1 2 3 4 _
highlight: 1..4
caption: the number line from 0 to 5: 1 to 4 is an unbroken run
```

**Example 2**

```
Input:  nums = [0, 3, 7, 2, 5, 8, 4, 6, 0, 1]
Output: 9
```

Every value from 0 to 8 is present. The second 0 doesn't make the run longer.

**Example 3**

```
Input:  nums = [1, 5, 2, 7]
Output: 2
```

1 and 2 form a run; 5 and 7 stand alone.

**Constraints**

- `0 <= len(nums) <= 10^5`
- `-10^9 <= nums[i] <= 10^9`

**Follow-up:** sorting solves it in O(n log n). Can you do it in O(n)?
