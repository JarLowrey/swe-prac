class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class Solution:
    def invertTree(self, root: TreeNode | None) -> TreeNode | None:
        # An empty tree is its own mirror image. This is also the base case below every leaf.
        if root is None:
            return None
        # Mirror both subtrees, then attach each on the opposite side. Python evaluates the
        # whole right-hand side (both calls, each given an original child) before assigning
        # either attribute. Assigning root.left first and then calling invertTree(root.left)
        # would mirror the wrong subtree and lose the other one.
        root.left, root.right = self.invertTree(root.right), self.invertTree(root.left)
        # The tree was changed in place: the root is still the root.
        return root
