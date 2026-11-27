#include <bits/stdc++.h>
using namespace std;

class Solution {
public:
    Node* cloneGraph(Node* node) {
        if (!node) return nullptr;
        unordered_map<Node*, Node*> copies;
        queue<Node*> todo;
        copies[node] = new Node(node->val);
        todo.push(node);
        while (!todo.empty()) {
            Node* current = todo.front();
            todo.pop();
            for (Node* next : current->neighbors) {
                if (!copies.count(next)) {
                    copies[next] = new Node(next->val);
                    todo.push(next);
                }
                copies[current]->neighbors.push_back(copies[next]);
            }
        }
        return copies[node];
    }
};
