Given an integer array `nums`, return an array `answer` of the same length where `answer[i]` is
the product of every element of `nums` except `nums[i]`.

Don't use division, and run in O(n) time.

**Example 1**

```
Input:  nums = [1, 2, 3, 4]
Output: [24, 12, 8, 6]
```

`answer[0] = 2 × 3 × 4 = 24`, `answer[1] = 1 × 3 × 4 = 12`, and so on.

```array
label: nums
values: 1 2 3 4
pointers: i=2
highlight: 0 1 3
caption: answer[2] = 1 × 2 × 4 = 8
```

**Example 2**

```
Input:  nums = [-1, 1, 0, -3, 3]
Output: [0, 0, 9, 0, 0]
```

Every product except the one that skips the 0 includes the 0. The one that skips it is
`-1 × 1 × -3 × 3 = 9`.

**Example 3**

```
Input:  nums = [2, 3, 4]
Output: [12, 8, 6]
```

**Constraints**

- `0 <= len(nums) <= 10^5`
- `-30 <= nums[i] <= 30`
- The product of any prefix or suffix of `nums` fits in a 32-bit integer.
- With one element the answer is `[1]`: the product of no numbers is 1.

**Follow-up:** can you use only O(1) extra space? The output array doesn't count.
