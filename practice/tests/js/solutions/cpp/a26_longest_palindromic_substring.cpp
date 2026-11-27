#include <bits/stdc++.h>
using namespace std;

class Solution {
public:
    string longestPalindrome(string s) {
        int start = 0, end = 0;
        for (int i = 0; i < (int)s.size(); i++) {
            for (auto [lo, hi] : {expand(s, i, i), expand(s, i, i + 1)}) {
                if (hi - lo > end - start) {
                    start = lo;
                    end = hi;
                }
            }
        }
        return s.substr(start, end - start);
    }

private:
    pair<int, int> expand(const string& s, int lo, int hi) {
        while (lo >= 0 && hi < (int)s.size() && s[lo] == s[hi]) {
            lo--;
            hi++;
        }
        return {lo + 1, hi};
    }
};
