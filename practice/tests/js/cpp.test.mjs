// C++: the compiler and runner on the built site's clang (see compiled-suite.mjs).
import { compiledSuite } from "./compiled-suite.mjs";

const TWO_SUM = `#include <bits/stdc++.h>
using namespace std;

class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        BODY
        unordered_map<int, int> seen;
        for (int i = 0; i < (int)nums.size(); i++) {
            auto it = seen.find(target - nums[i]);
            if (it != seen.end()) return {it->second, i};
            seen[nums[i]] = i;
        }
        return {};
    }
};
`;

const twoSum = (body) => TWO_SUM.replace("BODY", body);

compiledSuite("cpp", {
  solutions: {
    twoSum: twoSum('cout << "n=" << nums.size() << "\\n";'),
    twoSumNaive: twoSum("for (int i = 0; i < (int)nums.size(); i++) for (int j = i + 1; j < (int)nums.size(); j++) if (nums[i] + nums[j] == target) return {i, j};"),
    // An index past the end: libc++'s checks stop the program.
    twoSumBroken: twoSum("if (nums.size() == 4) { vector<int> none; return {none[3]}; }"),
    twoSumThrows: twoSum("if (nums.size() == 4) { vector<int> none; return {none.at(3)}; }"),
    fileStore: `#include <bits/stdc++.h>
using namespace std;

class FileStore {
    unordered_map<string, int> files;

public:
    bool addFile(int timestamp, string name, int size) {
        return files.emplace(name, size).second;
    }

    optional<int> getFileSize(int timestamp, string name) {
        auto it = files.find(name);
        if (it == files.end()) return nullopt;
        return it->second;
    }

    optional<int> deleteFile(int timestamp, string name) {
        auto it = files.find(name);
        if (it == files.end()) return nullopt;
        int size = it->second;
        files.erase(it);
        return size;
    }
};
`,
    syntaxError: "#include <bits/stdc++.h>\nusing namespace std;\nclass Solution { public: vector<int> twoSum(vector<int>& nums, int target) { return nums } };\n",
    renamed: twoSum("").replace("twoSum(", "twoSums("),
  },
  crash: /standard library check failed: vector\[\] index out of bounds/,
  thrown: /std::out_of_range \(vector\): exceptions are off here/,
  starterError: null, // the stubs return empty values: wrong answers, not errors
});
