Given the `root` of a binary tree, return its **maximum depth**: the number of nodes on the
longest path from the root down to a leaf. A leaf is a node with no children. An empty tree has
depth 0.

Trees are written in level order: the root, then its children, then their children, each level
left to right, with `None` where a child is missing. Children of missing nodes are not listed.

**Example 1**

```
Input:  root = [3, 9, 20, None, None, 15, 7]
Output: 3
```

9 has no children and 20 has two, 15 and 7. The longest root-to-leaf paths are 3 → 20 → 15 and
3 → 20 → 7, with three nodes each.

```tree
values: 3 9 20 null null 15 7
highlight: 3 20 15
caption: 3 → 20 → 15 has three nodes: depth 3
```

**Example 2**

```
Input:  root = [1, None, 2, 3, 4]
Output: 3
```

The root has only a right child, 2, whose children are 3 and 4.

```tree
values: 1 null 2 3 4
highlight: 1 2 3
caption: 1 → 2 → 3 (or 1 → 2 → 4): depth 3
```

**Example 3**

```
Input:  root = []
Output: 0
```

An empty tree has no nodes at all.

**Constraints**

- The tree has between 0 and 10^4 nodes and is at most 1,000 levels deep.
- `-100 <= Node.val <= 100`
