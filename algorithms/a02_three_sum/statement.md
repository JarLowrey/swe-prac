Given an integer array `nums`, return every **distinct** triplet of values
`[nums[i], nums[j], nums[k]]` that adds up to zero, where `i`, `j` and `k` are three different
indices.

Two triplets with the same three values count as the same triplet, so each one appears only once
in the answer. Return the triplets in any order, and the values inside each triplet in any order.

**Example 1**

```
Input:  nums = [-1, 0, 1, 2, -1, -4]
Output: [[-1, -1, 2], [-1, 0, 1]]
```

`-1 + 0 + 1 = 0` can be made with either -1, but it is listed once. `-1 + -1 + 2 = 0` uses both
-1s, which is allowed: they are different elements.

```array
label: nums
values: -1 0 1 2 -1 -4
highlight: 0 1 2
caption: -1 + 0 + 1 = 0 (the same values with index 4 are not listed again)
---
label: nums
values: -1 0 1 2 -1 -4
highlight: 0 3 4
caption: -1 + 2 + -1 = 0: two different elements that are both -1
```

**Example 2**

```
Input:  nums = [-3, -3, 1, 2]
Output: [[-3, 1, 2]]
```

`-3 + 1 + 2 = 0` works with either -3, but it is one triplet.

**Example 3**

```
Input:  nums = [0, 1, 1]
Output: []
```

The only triplet adds up to 2.

**Constraints**

- `0 <= len(nums) <= 3000`
- `-10^5 <= nums[i] <= 10^5`

**Follow-up:** checking every triple is O(n³). Can you do it in O(n²)?
