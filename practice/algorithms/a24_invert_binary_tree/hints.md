**Hint 1.** Look at one node. In the mirror image, what used to be its left subtree is on the right,
and that subtree is itself mirrored. The same holds for the right subtree.

**Hint 2.** So: invert the left subtree, invert the right subtree, then attach each on the opposite
side. An empty tree (`None`) is its own mirror image: that is the base case.

**Hint 3.** The swaps at different nodes don't interfere with each other, because a swap moves
whole subtrees. Any traversal that visits every node once and swaps its children works: recursion
(depth-first), or a queue (level by level).

**Hint 4.** Watch the assignment order. `root.left = invert(root.right)` followed by
`root.right = invert(root.left)` reads the *new* `root.left`. Save the children first, or assign
both at once with `root.left, root.right = ..., ...`.
