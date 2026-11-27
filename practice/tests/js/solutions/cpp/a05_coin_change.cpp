#include <bits/stdc++.h>
using namespace std;

class Solution {
public:
    int coinChange(vector<int>& coins, int amount) {
        vector<int> fewest(amount + 1, INT_MAX);
        fewest[0] = 0;
        for (int a = 1; a <= amount; a++) {
            for (int c : coins) {
                if (c <= a && fewest[a - c] != INT_MAX && fewest[a - c] + 1 < fewest[a]) {
                    fewest[a] = fewest[a - c] + 1;
                }
            }
        }
        return fewest[amount] == INT_MAX ? -1 : fewest[amount];
    }
};
