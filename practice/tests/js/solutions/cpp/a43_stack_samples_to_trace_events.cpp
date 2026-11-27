#include <bits/stdc++.h>
using namespace std;

class Solution {
public:
    vector<tuple<string, int, string>> convert(vector<pair<int, vector<string>>>& samples) {
        vector<tuple<string, int, string>> events;
        vector<string> prev;
        for (const auto& [time, stack] : samples) {
            size_t common = 0, limit = min(prev.size(), stack.size());
            while (common < limit && prev[common] == stack[common]) common++;
            for (size_t i = prev.size(); i-- > common;) events.emplace_back("end", time, prev[i]);
            for (size_t i = common; i < stack.size(); i++) events.emplace_back("start", time, stack[i]);
            prev = stack;
        }
        return events;
    }
};
