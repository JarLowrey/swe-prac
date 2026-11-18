You are given an array `lists` of `k` linked lists. Each list is sorted in ascending order. Merge
them all into one sorted linked list and return its head.

**Example 1**

```
Input:  lists = [[1, 4, 5], [1, 3, 4], [2, 6]]
Output: [1, 1, 2, 3, 4, 4, 5, 6]
```

```linkedlist
label: lists[0]
values: 1 4 5
---
label: lists[1]
values: 1 3 4
---
label: lists[2]
values: 2 6
---
label: merged
values: 1 1 2 3 4 4 5 6
caption: every node of the three lists, in one sorted list
```

**Example 2**

```
Input:  lists = []
Output: []
```

There are no lists at all, so the result is the empty list (`None`).

**Example 3**

```
Input:  lists = [[]]
Output: []
```

One list, and it is empty.

**Constraints**

- `0 <= k <= 10^4`
- Each list has between 0 and 500 nodes and is sorted in ascending order.
- The total number of nodes is at most `10^4`.
- `-10^4 <= Node.val <= 10^4`
