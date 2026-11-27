#include <bits/stdc++.h>
using namespace std;

class Solution {
public:
    void reorderList(ListNode* head) {
        if (!head || !head->next) return;
        ListNode *slow = head, *fast = head;
        while (fast->next && fast->next->next) {
            slow = slow->next;
            fast = fast->next->next;
        }
        ListNode *second = nullptr, *node = slow->next;
        slow->next = nullptr;
        while (node) {
            ListNode* next = node->next;
            node->next = second;
            second = node;
            node = next;
        }
        ListNode* first = head;
        while (second) {
            ListNode *firstNext = first->next, *secondNext = second->next;
            first->next = second;
            second->next = firstNext;
            first = firstNext;
            second = secondNext;
        }
    }
};
