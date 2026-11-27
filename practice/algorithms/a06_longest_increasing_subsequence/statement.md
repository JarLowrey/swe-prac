Given an integer array `nums`, return the length of its longest **strictly increasing
subsequence**.

A subsequence keeps some of the elements, in their original order: delete any number of elements
(possibly none) but don't rearrange the rest. `[3, 6, 2, 7]` is a subsequence of
`[0, 3, 1, 6, 2, 2, 7]`; `[6, 3]` is not. Strictly increasing means each element is larger than
the one before it, so equal values can't both be used.

**Example 1**

```
Input:  nums = [10, 9, 2, 5, 3, 7, 101, 18]
Output: 4
```

`[2, 3, 7, 101]` is one longest increasing subsequence; `[2, 5, 7, 18]` is another. No increasing
subsequence has 5 elements.

```array
label: nums
values: 10 9 2 5 3 7 101 18
highlight: 2 4 5 6
caption: 2, 3, 7, 101: increasing, and in the original order
```

**Example 2**

```
Input:  nums = [0, 1, 0, 3, 2, 3]
Output: 4
```

`[0, 1, 2, 3]`.

**Example 3**

```
Input:  nums = [7, 7, 7, 7, 7, 7, 7]
Output: 1
```

Equal values don't count as increasing, so the best is a single 7.

**Constraints**

- `1 <= len(nums) <= 2500`
- `-10^4 <= nums[i] <= 10^4`

**Follow-up:** the usual dynamic programming solution is O(n²). Can you do it in O(n log n)?
