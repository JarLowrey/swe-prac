Given the `root` of a binary tree, return the values of its nodes **level by level**: a list with
one inner list per level, from the root's level down, each listing that level's values from left
to right.

Trees are written in level order: the root, then each level left to right, with `None` where a
child is missing.

**Example 1**

```
Input:  root = [3, 9, 20, None, None, 15, 7]
Output: [[3], [9, 20], [15, 7]]
```

```tree
values: 3 9 20 null null 15 7
highlight: 9 20
caption: the second level, left to right: [9, 20]
```

**Example 2**

```
Input:  root = [1, 2, 3, 4, None, None, 5]
Output: [[1], [2, 3], [4, 5]]
```

4 and 5 have different parents, but they are the same distance from the root, so they share a
level.

```tree
values: 1 2 3 4 null null 5
highlight: 4 5
caption: the third level: [4, 5]
```

**Example 3**

```
Input:  root = []
Output: []
```

An empty tree has no levels.

**Constraints**

- The tree has between 0 and 10^4 nodes and is at most 1,000 levels deep.
- `-1000 <= Node.val <= 1000`
