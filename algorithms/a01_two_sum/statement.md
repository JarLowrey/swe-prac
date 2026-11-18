Given an array of integers `nums` and an integer `target`, return the indices of the two numbers
that add up to `target`.

Every input has exactly one answer, and you may not use the same element twice. Return the two
indices in any order.

**Example 1**

```
Input:  nums = [2, 7, 11, 15], target = 9
Output: [0, 1]
```

`nums[0] + nums[1] = 2 + 7 = 9`.

```array
label: nums
values: 2 7 11 15
highlight: 0 1
caption: 2 + 7 = 9
```

**Example 2**

```
Input:  nums = [3, 2, 4], target = 6
Output: [1, 2]
```

`3 + 3` would be 6, but there is only one 3, and an element can't be used twice.

**Example 3**

```
Input:  nums = [3, 3], target = 6
Output: [0, 1]
```

**Constraints**

- `2 <= len(nums) <= 10^4`
- `-10^9 <= nums[i], target <= 10^9`
- Exactly one pair adds up to `target`.

**Follow-up:** checking every pair is O(n²). Can you do it in O(n) time?
