#include <bits/stdc++.h>
using namespace std;

class Solution {
public:
    bool wordBreak(string s, vector<string>& wordDict) {
        unordered_set<string> words(wordDict.begin(), wordDict.end());
        set<int> lengths;
        for (const string& w : words) lengths.insert(w.size());
        int n = s.size();
        vector<bool> ok(n + 1, false);
        ok[n] = true;
        for (int i = n - 1; i >= 0; i--) {
            for (int length : lengths) {
                int j = i + length;
                if (j > n) break;
                if (ok[j] && words.count(s.substr(i, length))) {
                    ok[i] = true;
                    break;
                }
            }
        }
        return ok[0];
    }
};
