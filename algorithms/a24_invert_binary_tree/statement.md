Given the `root` of a binary tree, **invert** it and return its root. Inverting a tree turns it
into its mirror image: at every node, the left and right children swap places, taking their
whole subtrees with them.

You may change the tree in place and return the same `root`, or build a new tree. Trees are
written in level order: the root, then each level left to right, with `None` where a child is
missing.

**Example 1**

```
Input:  root = [4, 2, 7, 1, 3, 6, 9]
Output: [4, 7, 2, 9, 6, 3, 1]
```

```tree
values: 4 2 7 1 3 6 9
caption: before
---
values: 4 7 2 9 6 3 1
caption: after: the mirror image, reflected in a vertical line through the root
```

**Example 2**

```
Input:  root = [1, 2, 3, 4, 5]
Output: [1, 3, 2, None, None, 5, 4]
```

2 moves to the right of the root and takes its children 4 and 5 with it, and they swap too.

```tree
values: 1 2 3 4 5
highlight: 2 4 5
caption: before
---
values: 1 3 2 null null 5 4
highlight: 2 4 5
caption: after
```

**Example 3**

```
Input:  root = []
Output: []
```

**Constraints**

- The tree has between 0 and 10^4 nodes and is at most 1,000 levels deep.
- `-100 <= Node.val <= 100`
