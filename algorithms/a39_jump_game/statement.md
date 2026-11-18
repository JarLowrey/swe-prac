You are given an integer array `nums`. You start at index 0, and `nums[i]` is the **maximum**
length of a jump from index `i`: from `i` you may jump to any index from `i + 1` up to
`i + nums[i]`. Return `True` if you can reach the last index, and `False` otherwise.

**Example 1**

```
Input:  nums = [2, 3, 1, 1, 4]
Output: True
```

Jump 1 step from index 0 to index 1, then 3 steps to the last index.

```array
label: nums
values: 2 3 1 1 4
highlight: 0 1 4
caption: 0 → 1 → 4
```

**Example 2**

```
Input:  nums = [3, 2, 1, 0, 4]
Output: False
```

Every route lands on index 3, whose 0 lets you go nowhere, and no jump passes over it.

**Example 3**

```
Input:  nums = [0]
Output: True
```

You start on the last index, so there is nothing to do.

**Constraints**

- `1 <= len(nums) <= 2 * 10^4`
- `0 <= nums[i] <= 10^5`
