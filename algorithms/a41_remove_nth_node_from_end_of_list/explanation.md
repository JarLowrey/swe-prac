## Understand the problem

Positions are counted from the end: the last node is the 1st from the end.

```linkedlist
values: 1 2 3 4
pointers: 4th=0 3rd=1 2nd=2 1st=3
highlight: 2
caption: positions from the end: with n = 2 we remove 3
```

A singly linked list only links forwards, so a node can't be unlinked from where it stands. We
need the node **before** it and make that node skip over it:

```linkedlist
values: 1 2 3 4
pointers: before=1
highlight: 2
caption: before.next = before.next.next skips 3
---
values: 1 2 4
caption: the result: [1, 2, 4]
```

Cases to check before coding:

- **`n = 1`**: the last node goes (Example 2).
- **`n` equal to the length**: the head itself goes. It has no node before it, and the new head is
  `head.next`. This is why the method returns a head at all.
- **One node**: removing it leaves `None` (Example 3).
- **Repeated values**: `[1, 2, 1, 2, 1]` with `n = 2` removes the second 2. Remove by position,
  never by value.

## Brute force: count, then walk

Two passes: count the nodes, then walk to the node just before position `L - n`:

```python
def removeNthFromEnd(self, head: ListNode | None, n: int) -> ListNode | None:
    length, node = 0, head
    while node:
        length, node = length + 1, node.next
    if n == length:  # removing the head: nothing comes before it
        return head.next
    before = head
    for _ in range(length - n - 1):  # stop on the node before the target
        before = before.next
    before.next = before.next.next
    return head
```

**O(L) time** for a list of L nodes, **O(1) space**. That is already optimal in big O, so the
interviewer's real question is the follow-up: can you do it in one pass? (A genuinely slow
version exists too: for each node, count the nodes after it to see whether it is the n-th from
the end. That's O(L²), and the hidden tests on 20,000 nodes reject it.)

## The key insight: a gap of n nodes

Keep two pointers exactly `n` nodes apart and move them together. When `fast` reaches the last
node, `slow` is `n` nodes behind it: the (n + 1)-th node from the end, which is the node just
before the one to remove. The gap works like a ruler laid down from the end of the list.

Both pointers start at a **dummy node** placed in front of `head`, so that even the head has a
node before it. Example 1, with `n = 2`:

```linkedlist
values: dummy 1 2 3 4
pointers: slow=0 fast=0
caption: both start at the dummy node in front of head
---
values: dummy 1 2 3 4
pointers: slow=0 fast=2
caption: fast moves n = 2 nodes ahead
---
values: dummy 1 2 3 4
pointers: slow=1 fast=3
caption: both move one step: the gap stays 2
---
values: dummy 1 2 3 4
pointers: slow=2 fast=4
highlight: 3
caption: fast is on the last node, so slow is just before the 2nd from the end
---
values: dummy 1 2 4
pointers: slow=2
caption: slow.next = slow.next.next, then return dummy.next
```

### Removing the head

With `n` equal to the length, `fast` reaches the last node while opening the gap, the loop never
runs, and `slow` is still on the dummy node: exactly the node before the head.

```linkedlist
values: dummy 1 2 3
pointers: slow=0 fast=3
highlight: 1
caption: n = 3: fast is already on the last node, and slow is on dummy
---
values: dummy 2 3
pointers: slow=0
caption: dummy.next = dummy.next.next drops the old head; dummy.next is the new head
```

Without a dummy node it needs a special case. Start both pointers at `head` and move `fast`
`n` nodes; if that runs `fast` off the end (`None`), `n` is the length and the head goes:

```python
fast = slow = head
for _ in range(n):
    fast = fast.next
if fast is None:  # n == length: remove the head
    return head.next
while fast.next:
    fast, slow = fast.next, slow.next
slow.next = slow.next.next
return head
```

Both are correct. The dummy node is the general trick whenever the head might change; see
[linked list techniques](#/algo/learn/patterns/linked-list-techniques).

## The solution

```solution
```

**Why it works.** After the first loop `fast` is `n` nodes after `slow`, and each step of the
second loop moves both, so the gap stays `n`. That loop stops with `fast` on the last node, so
`slow` is `n` nodes before the last node: position `n + 1` from the end, counting the dummy
node as part of the list. That is the node before the target, even when the target is the head.
`fast` can't run off the list while opening the gap, because `n` is at most the length and
`fast` starts one node before `head`.

## Complexity

- **Time: O(L).** `fast` walks the whole list once, and `slow` makes `L - n` moves behind it.
- **Space: O(1).** Two pointers and one dummy node.

"One pass" doesn't mean less work. The two pointers take about `L + (L - n)` steps between them,
the same as counting (`L`) and then walking (`L - n`). The one-pass version has one loop instead
of two, and when `n` is small `slow` touches nodes `fast` has just visited, which are still in
cache: a small constant-factor edge, not a big-O one. Saying so when asked "which is faster?"
shows you know what each version costs.

## Pitfalls and variations

**A gap one too small.** `slow` must stop on the node *before* the target. With a gap of `n - 1`
it lands on the target itself, and a singly linked list has no way back to the node before:

```linkedlist
values: dummy 1 2 3 4
pointers: slow=3 fast=4
highlight: 3
caption: a gap of 1 for n = 2: slow is on 3 itself, and can't step back to 2
```

Two correct ways to write it: move `fast` `n` nodes ahead and loop `while fast.next`, or move it
`n + 1` nodes ahead and loop `while fast`, letting it run off the end. Check your version on
`[1]` with `n = 1` and `[1, 2]` with `n = 2`.

- **No dummy and no special case.** If the head is the target, `fast` is `None` after the first
  loop and `fast.next` raises `AttributeError`.
- **Returning `head` instead of `dummy.next`.** When the head was removed, `head` still points at
  the removed node, whose `next` is unchanged: `[1, 2, 3]` with `n = 3` comes back as
  `[1, 2, 3]` instead of `[2, 3]`.
- **Removing by value.** Values can repeat, so search by position only.
- **Follow-up: `n` may be larger than the length.** `fast` becomes `None` while opening the gap;
  check it inside that loop and return the list unchanged (or raise).
- **Follow-up: a stream you can read only once.** Two pointers both walk the list, so they read
  it twice. Keep the last `n + 1` nodes in `collections.deque(maxlen=n + 1)`: when the stream
  ends, the oldest node in the deque is the one before the target (if the stream had exactly `n`
  nodes, the head itself goes).
- **The same gap** finds the k-th node from the end, and Rotate List uses it to find the new
  tail. Pointers moving at different speeds instead find the middle, as in
  [Reorder List](#/algo/problem/a40_reorder_list); dummy nodes also keep merging simple, as in
  [Merge k Sorted Lists](#/algo/problem/a42_merge_k_sorted_lists).

More on the structure itself: [linked lists](#/algo/learn/data-structures/linked-lists) and
[two pointers](#/algo/learn/patterns/two-pointers).
