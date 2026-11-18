You are planning to rob houses along a street. `nums[i]` is the amount of money in house `i`.
Adjacent houses have connected alarms: robbing two houses next to each other alerts the police.

Return the most money you can rob without robbing two adjacent houses.

**Example 1**

```
Input:  nums = [1, 2, 3, 1]
Output: 4
```

Rob house 0 and house 2: `1 + 3 = 4`.

**Example 2**

```
Input:  nums = [2, 7, 9, 3, 1]
Output: 12
```

Rob houses 0, 2 and 4: `2 + 9 + 1 = 12`.

```array
label: nums
values: 2 7 9 3 1
highlight: 0 2 4
caption: 2 + 9 + 1 = 12, and no two robbed houses are next to each other
```

**Example 3**

```
Input:  nums = [2, 1, 1, 2]
Output: 4
```

Rob houses 0 and 3. Skipping two houses in a row can be the best plan.

**Constraints**

- `1 <= len(nums) <= 100`
- `0 <= nums[i] <= 400`
