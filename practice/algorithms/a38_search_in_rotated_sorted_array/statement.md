An array of distinct integers was sorted in ascending order and then possibly **rotated** at an
unknown index `k`: the part from index `k` on was moved to the front. For example,
`[0, 1, 2, 3, 4, 5, 6]` rotated at index 3 becomes `[3, 4, 5, 6, 0, 1, 2]`. With `k = 0` the array
is unchanged.

Given the rotated array `nums` and an integer `target`, return the index of `target` in `nums`,
or `-1` if it isn't there.

Your algorithm must run in O(log n) time.

**Example 1**

```
Input:  nums = [4, 5, 6, 7, 0, 1, 2], target = 0
Output: 4
```

```array
label: nums
values: 4 5 6 7 0 1 2
highlight: 4
caption: two sorted runs, 4 5 6 7 and 0 1 2; the target 0 is at index 4
```

**Example 2**

```
Input:  nums = [4, 5, 6, 7, 0, 1, 2], target = 3
Output: -1
```

3 would sit between 2 and 4 in the sorted order, but it isn't in the array.

**Example 3**

```
Input:  nums = [1], target = 0
Output: -1
```

**Constraints**

- `1 <= len(nums) <= 5000`
- `-10^4 <= nums[i], target <= 10^4`
- All values of `nums` are distinct.
- `nums` is an ascending array, possibly rotated.
