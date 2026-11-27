**Hint 1.** A deep copy needs one new node per original node, so you have to visit every node:
a depth-first or breadth-first walk. But the graph has cycles (in Example 1, and in fact every
edge goes both ways). How do you avoid walking round forever?

**Hint 2.** Keep a dict from each original node to its copy. It is your visited set, and it also
tells you which copy to link to when you meet a node that was already copied.

**Hint 3.** Put a node's copy in the dict *before* you copy its neighbours. When the walk comes
back round a cycle to that node, it finds the copy instead of starting another one.

**Hint 4.** Recursively: `clone(n)` returns `copies[n]` if it exists; otherwise it makes a new node,
records it, appends `clone(m)` for each neighbour `m` in order, and returns the new node. Return
`None` for an empty graph.
