#include <bits/stdc++.h>
using namespace std;

class InMemoryDB {
    struct Field {
        string value;
        double expiresAt; // alive while timestamp < expiresAt; in a backup, the time it had left
    };
    using Fields = map<string, Field>;

    unordered_map<string, Fields> data;
    vector<pair<int, unordered_map<string, Fields>>> backups;

    Fields live(int timestamp, const string& key) {
        Fields out;
        auto it = data.find(key);
        if (it != data.end()) {
            for (const auto& [name, f] : it->second) {
                if (timestamp < f.expiresAt) out.emplace(name, f);
            }
        }
        return out;
    }

    static string format(const Fields& fields) {
        string out;
        for (const auto& [name, f] : fields) {
            if (!out.empty()) out += ", ";
            out += name + "(" + f.value + ")";
        }
        return out;
    }

public:
    InMemoryDB() {
    }

    void set(int timestamp, string key, string field, string value) {
        data[key][field] = Field{value, INFINITY};
    }

    optional<string> get(int timestamp, string key, string field) {
        Fields fields = live(timestamp, key);
        auto it = fields.find(field);
        if (it == fields.end()) return nullopt;
        return it->second.value;
    }

    bool delete_(int timestamp, string key, string field) {
        if (!live(timestamp, key).count(field)) return false;
        Fields& fields = data[key];
        fields.erase(field);
        if (fields.empty()) data.erase(key);
        return true;
    }

    string scan(int timestamp, string key) {
        return format(live(timestamp, key));
    }

    string scanByPrefix(int timestamp, string key, string prefix) {
        Fields matching;
        for (const auto& [name, f] : live(timestamp, key)) {
            if (name.starts_with(prefix)) matching.emplace(name, f);
        }
        return format(matching);
    }

    void setWithTtl(int timestamp, string key, string field, string value, int ttl) {
        data[key][field] = Field{value, (double)timestamp + ttl};
    }

    int backup(int timestamp) {
        unordered_map<string, Fields> snapshot;
        for (const auto& entry : data) {
            Fields fields;
            for (const auto& [name, f] : live(timestamp, entry.first)) {
                fields.emplace(name, Field{f.value, f.expiresAt - timestamp});
            }
            if (!fields.empty()) snapshot.emplace(entry.first, fields);
        }
        backups.emplace_back(timestamp, snapshot);
        return snapshot.size();
    }

    void restore(int timestamp, int timestampToRestore) {
        int i = backups.size() - 1;
        while (backups[i].first > timestampToRestore) i--;
        data.clear();
        for (const auto& [key, fields] : backups[i].second) {
            for (const auto& [name, f] : fields) data[key].emplace(name, Field{f.value, timestamp + f.expiresAt});
        }
    }
};
