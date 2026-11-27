class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class Solution:
    def reorderList(self, head: ListNode | None) -> None:
        # Nothing to reorder in a list of zero or one nodes (and fast.next would crash).
        if head is None or head.next is None:
            return
        middle = self.end_of_first_half(head)
        second = self.reverse(middle.next)
        middle.next = None  # cut: otherwise the merged list ends in a cycle
        self.weave(head, second)

    def end_of_first_half(self, head: ListNode) -> ListNode:
        # slow moves 1 step, fast 2: when fast can't take two more, slow is the middle.
        # For an even length it stops on the left middle, so the first half is the longer one.
        slow = fast = head
        while fast.next and fast.next.next:
            slow = slow.next
            fast = fast.next.next
        return slow

    def reverse(self, node: ListNode | None) -> ListNode | None:
        prev = None
        while node:
            nxt = node.next  # save the rest before overwriting the pointer
            node.next = prev
            prev, node = node, nxt
        return prev  # the old tail is the new head

    def weave(self, first: ListNode, second: ListNode | None) -> None:
        # second is as long as first, or one node shorter: stop when it runs out. first's last
        # node is then already in place, with next = None from the cut.
        while second:
            first_next, second_next = first.next, second.next
            first.next = second
            second.next = first_next
            first, second = first_next, second_next
