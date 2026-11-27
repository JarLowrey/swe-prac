**Hint 1.** With an array you'd just read from both ends. A singly linked list can't walk
backwards, and an array of nodes costs O(n) space. What would make the back of the list easy to
walk from its end?

**Hint 2.** Look at the output as two lists woven together: the front half in order, and the back
half *in reverse*.

**Hint 3.** That splits into three classic steps, each O(n) time and O(1) space: find the middle
(slow and fast pointers), reverse the second half, then merge the two halves alternately.

**Hint 4.** Cut the list at the middle (`middle.next = None`) before merging, or the last node
ends up pointing back into the list and you build a cycle.
