**Hint 1.** If you knew the length `L`, the node to remove would be at position `L - n` from the
front (counting from 0). Counting first and then walking works in two passes. Can you do it in
one?

**Hint 2.** To unlink a node from a singly linked list you need the node *before* it:
`before.next = before.next.next`. So the real goal is to stop one node early.

**Hint 3.** Use two pointers with a fixed gap. Move `fast` `n` nodes ahead of `slow`, then move
both one step at a time. When `fast` is on the last node, `slow` is just before the node to
remove.

**Hint 4.** Removing the head (`n` equal to the length) has no node before it. Start both
pointers at a dummy node whose `next` is `head`, and return `dummy.next` at the end.
