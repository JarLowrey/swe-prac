import heapq


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class Solution:
    def mergeKLists(self, lists: list[ListNode | None]) -> ListNode | None:
        # The heap holds the current head of every list that still has nodes, so at most k
        # entries and O(log k) per operation. Entries are (value, list index, node): the index
        # breaks ties between equal values, so heapq never compares two ListNodes (which raises
        # TypeError). Each list has at most one entry at a time, so the index is unique.
        heap = [(node.val, i, node) for i, node in enumerate(lists) if node]  # skip empty lists
        heapq.heapify(heap)  # O(k)

        dummy = tail = ListNode()  # a placeholder in front of the output: no first-node case
        while heap:
            _, i, node = heapq.heappop(heap)  # the smallest node not merged yet
            tail.next = node  # relink the existing node instead of copying it
            tail = node
            if node.next:
                # Its list's next node becomes that list's head.
                heapq.heappush(heap, (node.next.val, i, node.next))
        # The last node popped was the last of its list, so its next is already None.
        return dummy.next
