class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class Solution:
    def removeNthFromEnd(self, head: ListNode | None, n: int) -> ListNode | None:
        # A dummy node in front of head gives every node, the head included, a node before it.
        # Removing the head is then the same as removing any other node: no special case.
        dummy = ListNode(0, head)

        # Open a gap of n nodes between slow and fast. n is at most the length and fast starts
        # one node before head, so fast never runs off the list here.
        slow = fast = dummy
        for _ in range(n):
            fast = fast.next

        # Move both until fast is on the last node. The gap is still n, so slow is now the
        # (n + 1)-th node from the end: the node just before the one to remove.
        while fast.next:
            slow = slow.next
            fast = fast.next

        slow.next = slow.next.next  # unlink the n-th node from the end
        # Not `head`: if the head was the node removed, dummy.next is the new head.
        return dummy.next
