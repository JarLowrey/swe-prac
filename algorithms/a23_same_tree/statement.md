Given the roots `p` and `q` of two binary trees, return `True` if they are the same tree: they
have exactly the same shape, and every pair of nodes in matching positions holds the same value.

Trees are written in level order: the root, then each level left to right, with `None` where a
child is missing.

**Example 1**

```
Input:  p = [1, 2, 3], q = [1, 2, 3]
Output: True
```

```tree
values: 1 2 3
caption: p
---
values: 1 2 3
caption: q: same shape, same values
```

**Example 2**

```
Input:  p = [1, 2], q = [1, None, 2]
Output: False
```

The values are the same, but 2 is the left child of 1 in `p` and the right child in `q`.

```tree
values: 1 2
highlight: 2
caption: p: 2 is a left child
---
values: 1 null 2
highlight: 2
caption: q: 2 is a right child
```

**Example 3**

```
Input:  p = [1, 2, 1], q = [1, 1, 2]
Output: False
```

The shapes match, but the left children hold 2 and 1.

**Constraints**

- Each tree has between 0 and 10^4 nodes and is at most 1,000 levels deep.
- `-10^4 <= Node.val <= 10^4`
