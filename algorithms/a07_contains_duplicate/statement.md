Given an integer array `nums`, return `True` if some value appears at least twice, and `False` if
every element is distinct.

**Example 1**

```
Input:  nums = [1, 2, 2, 3, 4]
Output: True
```

The value 2 appears twice, at indices 1 and 2.

```array
label: nums
values: 1 2 2 3 4
highlight: 1 2
caption: 2 appears twice
```

**Example 2**

```
Input:  nums = [1, 2, 3, 4]
Output: False
```

All four values are different.

**Example 3**

```
Input:  nums = [3, 1, 4, 1, 5, 9, 2, 6]
Output: True
```

The two 1s are at indices 1 and 3: a duplicate doesn't have to sit next to its twin.

**Constraints**

- `0 <= len(nums) <= 10^5`
- `-10^9 <= nums[i] <= 10^9`

**Follow-up:** comparing every pair is O(n²). Can you do it in O(n) time?
