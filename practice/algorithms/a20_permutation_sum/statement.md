Given an array `nums` of distinct positive integers and a positive integer `target`, return the
number of **ordered** sequences of numbers from `nums` that add up to `target`.

Each number may be used any number of times, and order matters: `1 + 3` and `3 + 1` are two
different sequences.

**Example 1**

```
Input:  nums = [1, 2, 3], target = 4
Output: 7
```

The seven sequences are:

```
1 + 1 + 1 + 1
1 + 1 + 2      1 + 2 + 1      2 + 1 + 1
1 + 3          3 + 1
2 + 2
```

**Example 2**

```
Input:  nums = [9], target = 3
Output: 0
```

9 is already bigger than the target.

**Example 3**

```
Input:  nums = [5, 3], target = 8
Output: 2
```

`5 + 3` and `3 + 5`: the same numbers in a different order count twice.

**Constraints**

- `1 <= len(nums) <= 200`
- `1 <= nums[i] <= 1000`, and the numbers are all different
- `1 <= target <= 1000`
- The answer fits in a 32-bit signed integer.
