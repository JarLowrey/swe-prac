class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class Solution:
    def isSameTree(self, p: TreeNode | None, q: TreeNode | None) -> bool:
        # Walk both trees in lockstep, always comparing the nodes in the same position.

        # Both missing: two empty (sub)trees are the same. Every successful comparison ends
        # here, below the leaves.
        if p is None and q is None:
            return True
        # Exactly one missing: the shapes differ at this position. This check must come
        # before reading p.val or q.val.
        if p is None or q is None:
            return False
        # Both present: the values must match...
        if p.val != q.val:
            return False
        # ...and so must both pairs of subtrees. `and` skips the right subtrees when the left
        # ones differ, so the walk stops at the first difference it finds.
        return self.isSameTree(p.left, q.left) and self.isSameTree(p.right, q.right)
