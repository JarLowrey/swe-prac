class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class Solution:
    def maxDepth(self, root: TreeNode | None) -> int:
        # An empty tree has no nodes on any path. This is also the base case that stops the
        # recursion below every leaf (a leaf's two children are both None).
        if root is None:
            return 0
        # The longest path down from this node goes through the deeper of its two subtrees,
        # plus this node itself. Each call returns after its children's calls, so the answers
        # are built bottom-up, leaves first.
        #
        # The recursion is as deep as the tree is tall. For very tall trees, the level-by-level
        # (BFS) version in the explanation avoids recursion altogether.
        return 1 + max(self.maxDepth(root.left), self.maxDepth(root.right))
