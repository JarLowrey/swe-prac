class Node:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []


class Solution:
    def cloneGraph(self, node: Node | None) -> Node | None:
        # An empty graph has nothing to copy.
        if node is None:
            return None

        # Each original node -> its copy. This is the visited set (a node in here is copied, or
        # being copied) and the lookup for linking to copies made earlier. Keys are the node
        # objects, hashed by identity, so this works even if two nodes shared a value.
        copies: dict[Node, Node] = {}

        def clone(original: Node) -> Node:
            if original in copies:
                return copies[original]
            copy = Node(original.val)
            # Record the copy BEFORE visiting the neighbours. Every edge goes both ways, so
            # some neighbour leads straight back here; it must find this copy rather than start
            # another (which would recurse forever).
            copies[original] = copy
            for neighbor in original.neighbors:
                # Same order as the original's list. clone() returns the existing copy for a
                # node already seen, or copies it (and everything reachable from it) now.
                copy.neighbors.append(clone(neighbor))
            return copy

        return clone(node)
