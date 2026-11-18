Given the `head` of a singly linked list and an integer `n`, remove the `n`-th node from the end
of the list and return the head of the changed list.

`n = 1` means the last node. `n` is always valid: between 1 and the length of the list.

**Example 1**

```
Input:  head = [1, 2, 3, 4], n = 2
Output: [1, 2, 4]
```

```linkedlist
values: 1 2 3 4
highlight: 2
caption: before: 3 is the 2nd node from the end
---
values: 1 2 4
caption: after
```

**Example 2**

```
Input:  head = [1, 2, 3], n = 1
Output: [1, 2]
```

`n = 1` removes the last node.

**Example 3**

```
Input:  head = [1], n = 1
Output: []
```

Removing the only node leaves an empty list, so return `None`.

**Constraints**

- The list has between 1 and 3 × 10^4 nodes.
- `0 <= Node.val <= 100`
- `1 <= n <=` the length of the list

**Follow-up:** can you do it in one pass over the list?
