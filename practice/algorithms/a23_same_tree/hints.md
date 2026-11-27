**Hint 1.** Two trees are the same when their roots match, their left subtrees are the same tree
and their right subtrees are the same tree. That sentence is already a recursive algorithm.

**Hint 2.** Work out the base cases first. What if both nodes are `None`? What if only one of them
is? Only once both exist can you compare `p.val` and `q.val`.

**Hint 3.** Comparing two traversals (say, both in-order lists) is not enough unless the lists also
record the missing children: `[2, 1]` and `[1, None, 2]` have the same in-order values `1, 2`.

**Hint 4.** Walk both trees in lockstep and return `False` at the first difference. `and`
short-circuits, so the right subtrees are only compared if the left ones matched.
