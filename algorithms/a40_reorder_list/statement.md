You are given the head of a singly linked list `L0 → L1 → … → Ln-1 → Ln`. Reorder it to

`L0 → Ln → L1 → Ln-1 → L2 → Ln-2 → …`

taking nodes alternately from the front and the back. Change the `next` pointers of the
existing nodes in place: the method returns nothing, and the test reads the list from `head`
afterwards. Use O(1) extra space.

**Example 1**

```
Input:  head = [1, 2, 3, 4]
Output: [1, 4, 2, 3]
```

```linkedlist
values: 1 2 3 4
caption: before
---
values: 1 4 2 3
highlight: 1 3
caption: after: the back half (4, 3) is woven between the front half (1, 2)
```

**Example 2**

```
Input:  head = [1, 2, 3, 4, 5]
Output: [1, 5, 2, 4, 3]
```

**Constraints**

- The list has between 0 and 5 × 10^4 nodes.
- `1 <= Node.val <= 1000` in the examples; values can be anything, only the order matters.
- Reorder the nodes; don't just copy values around (and don't allocate a new list).
