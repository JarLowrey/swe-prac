from collections import deque


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class Solution:
    def levelOrder(self, root: TreeNode | None) -> list[list[int]]:
        levels: list[list[int]] = []
        # A queue hands nodes back in the order they went in. Taking a node from the front and
        # adding its children at the back visits the tree level by level, left to right
        # (breadth-first search). An empty tree starts with an empty queue and returns [].
        queue = deque([root] if root else [])
        while queue:
            # Here the queue holds exactly one whole level: all of the level above has been
            # taken out, and none of this level's children have been added yet.
            level = []
            # range(len(queue)) is fixed when the loop starts, so the children added below wait
            # for the next round.
            for _ in range(len(queue)):
                node = queue.popleft()  # O(1) for a deque; list.pop(0) would be O(length)
                level.append(node.val)
                # Left before right keeps each level in left-to-right order. Missing children
                # are never queued.
                if node.left:
                    queue.append(node.left)
                if node.right:
                    queue.append(node.right)
            levels.append(level)
        return levels
