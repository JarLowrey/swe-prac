**Hint 1.** You know how to merge two sorted lists with two pointers. Merging the lists one at a
time into a growing result works, but count the work: the result is walked again for every list,
which is O(Nk) for N nodes in total.

**Hint 2.** At every step, the next node of the output is the smallest of the k current heads.
Scanning all k heads to find it is also O(k) per node. You need a structure that hands you the
smallest of k values quickly and lets you replace it.

**Hint 3.** A min-heap of the heads: pop the smallest node, append it to the output, and push
its `next` (if there is one) in its place. The heap never holds more than k nodes, so each step
is O(log k).

**Hint 4.** Python's `heapq` compares tuples element by element, and two `ListNode`s can't be
compared, so `(node.val, node)` crashes when two values are equal. Push
`(node.val, i, node)` with a unique tie-breaker `i`: the list's index works, because each list
has at most one node in the heap at a time.
