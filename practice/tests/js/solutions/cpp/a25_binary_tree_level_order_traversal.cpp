#include <bits/stdc++.h>
using namespace std;

class Solution {
public:
    vector<vector<int>> levelOrder(TreeNode* root) {
        vector<vector<int>> levels;
        if (!root) return levels;
        queue<TreeNode*> todo;
        todo.push(root);
        while (!todo.empty()) {
            vector<int> level;
            for (int i = todo.size(); i > 0; i--) {
                TreeNode* node = todo.front();
                todo.pop();
                level.push_back(node->val);
                if (node->left) todo.push(node->left);
                if (node->right) todo.push(node->right);
            }
            levels.push_back(level);
        }
        return levels;
    }
};
