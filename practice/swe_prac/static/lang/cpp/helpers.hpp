// For scratch.cpp: build the inputs the tests describe, and print values the way they do.
#pragma once

#include <initializer_list>
#include <optional>
#include <queue>
#include <vector>

#include "swe.hpp"

// show(value): a value as the tests write it: [1, 2], "text", null, true.
using swe::show;

// For makeTree: a missing child.
inline constexpr std::nullopt_t null = std::nullopt;

#ifdef SWE_LISTNODE
// makeList({1, 2, 3}) is 1 -> 2 -> 3 (nullptr for no values).
inline ListNode* makeList(std::initializer_list<int> values) {
    ListNode* head = nullptr;
    for (auto it = std::rbegin(values); it != std::rend(values); ++it) head = new ListNode(*it, head);
    return head;
}
#endif

#ifdef SWE_TREENODE
// makeTree({3, 9, 20, null, null, 15, 7}): level order, null for a missing child.
inline TreeNode* makeTree(std::initializer_list<std::optional<int>> values) {
    std::vector<std::optional<int>> v(values);
    if (v.empty() || !v[0]) return nullptr;
    TreeNode* root = new TreeNode(*v[0]);
    std::queue<TreeNode*> queue;
    queue.push(root);
    size_t i = 1;
    while (!queue.empty() && i < v.size()) {
        TreeNode* parent = queue.front();
        queue.pop();
        if (i < v.size() && v[i]) queue.push(parent->left = new TreeNode(*v[i]));
        i++;
        if (i < v.size() && v[i]) queue.push(parent->right = new TreeNode(*v[i]));
        i++;
    }
    return root;
}
#endif

#ifdef SWE_GRAPHNODE
// makeGraph({{2, 4}, {1, 3}}): row i lists node i+1's neighbors. Returns node 1.
inline Node* makeGraph(const std::vector<std::vector<int>>& adjacency) {
    std::vector<Node*> nodes;
    for (size_t i = 0; i < adjacency.size(); i++) nodes.push_back(new Node(static_cast<int>(i + 1)));
    for (size_t i = 0; i < adjacency.size(); i++)
        for (int w : adjacency[i]) nodes[i]->neighbors.push_back(nodes[w - 1]);
    return nodes.empty() ? nullptr : nodes[0];
}
#endif
