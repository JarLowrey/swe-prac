import java.util.*;

class Solution {
    public void reorderList(ListNode head) {
        if (head == null || head.next == null) return;
        ListNode slow = head, fast = head;
        while (fast.next != null && fast.next.next != null) {
            slow = slow.next;
            fast = fast.next.next;
        }
        ListNode second = null, node = slow.next;
        slow.next = null;
        while (node != null) {
            ListNode next = node.next;
            node.next = second;
            second = node;
            node = next;
        }
        ListNode first = head;
        while (second != null) {
            ListNode firstNext = first.next, secondNext = second.next;
            first.next = second;
            second.next = firstNext;
            first = firstNext;
            second = secondNext;
        }
    }
}
