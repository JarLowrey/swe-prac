**Hint 1.** A simple approach: find the height, then for each depth walk the tree from the root
collecting the nodes at that depth. It works, but how often does it visit the root? What does that
cost for a tree shaped like a long stick?

**Hint 2.** Which data structure hands things back in the order they went in? If you take a node
out and put its children in at the back, in what order do the nodes come out?

**Hint 3.** Breadth-first search with a queue visits the nodes level by level, left to right. To
know where one level ends, read `len(queue)` at the start of each round: exactly that many nodes
are the current level. (Or keep two lists, `level` and `next_level`.)

**Hint 4.** Use `collections.deque` and `popleft()`: `list.pop(0)` shifts every remaining element,
which is O(n) per pop. Return `[]` for an empty tree, and don't queue `None` children.
