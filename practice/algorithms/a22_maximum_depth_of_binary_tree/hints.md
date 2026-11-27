**Hint 1.** Suppose someone told you the maximum depth of the root's left subtree and of its right
subtree. What is the depth of the whole tree?

**Hint 2.** That is a recursive definition: `depth(node) = 1 + max(depth(left), depth(right))`.
What is the depth of an empty tree (`None`)? That is your base case, and it is what stops the
recursion below every leaf.

**Hint 3.** Without recursion: walk the tree one level at a time (breadth-first). Keep a list of
the nodes on the current level, build the list of their children, and count the levels until the
list is empty.

**Hint 4.** Both ways visit each node once, so O(n) time. Test with an empty tree (depth 0), a
single node (depth 1) and a tree where every node has only one child (depth n).
