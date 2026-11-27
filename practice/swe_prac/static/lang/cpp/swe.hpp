// The C++ test harness's shared part: JSON in and out, and the test loop (static/lang-runner.js
// drives it). A problem's generated main.cpp includes the solution, then this file, and calls
// swe::run with a function that calls the method a test step names.
//
// stdin holds the tests as JSON: {"tests": [{"steps": [{"call": "...", "args": [...]}]}]}. For
// each test, a fresh instance; each event goes to the page through the imported swe.emit:
//
//   {"e":"start"}                          a test begins
//   {"e":"call"}                           a step's call is about to start
//   {"e":"step","ms":1.5,"value":...}      it returned this (as JSON)
//   {"e":"step","adapter":"..."}           it returned a malformed list, tree or graph
//   {"e":"end"} ... {"e":"done"}
//
// A list, tree or graph is written as the tests write it (an empty one, or nullptr, is []).
// swe.emit returns 0 after a step that failed (the page compares the results), which ends the
// test. What the solution prints goes to stdout and stderr as usual.
#pragma once

#include <chrono>
#include <cmath>
#include <cstdio>
#include <iostream>
#include <iterator>
#include <optional>
#include <queue>
#include <string>
#include <tuple>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

extern "C" __attribute__((import_module("swe"), import_name("emit"))) int swe_emit(const char* text, int length);

namespace swe {

constexpr size_t MAX_NODES = 1000000;

// -- JSON values ---------------------------------------------------------------------------
struct Json {
    enum Kind { Null, Bool, Number, String, Array, Object } kind = Null;
    bool boolean = false;
    double number = 0;
    long long integer = 0;
    std::string text;
    std::vector<Json> items;
    std::vector<std::pair<std::string, Json>> fields;

    const Json& operator[](size_t i) const { return items[i]; }
    size_t size() const { return items.size(); }
    const Json& get(const std::string& key) const {
        static const Json none;
        for (const auto& [k, v] : fields)
            if (k == key) return v;
        return none;
    }
};

struct Parser {
    const std::string& s;
    size_t i = 0;

    void space() {
        while (i < s.size() && static_cast<unsigned char>(s[i]) <= ' ') i++;
    }

    std::string string() {
        std::string out;
        i++;  // opening quote
        while (i < s.size() && s[i] != '"') {
            char c = s[i++];
            if (c != '\\') {
                out += c;
                continue;
            }
            char e = s[i++];
            if (e == 'n') out += '\n';
            else if (e == 't') out += '\t';
            else if (e == 'r') out += '\r';
            else if (e == 'b') out += '\b';
            else if (e == 'f') out += '\f';
            else if (e == 'u') {
                unsigned code = std::stoul(s.substr(i, 4), nullptr, 16);
                i += 4;
                if (code >= 0xd800 && code < 0xdc00 && s.compare(i, 2, "\\u") == 0) {
                    unsigned low = std::stoul(s.substr(i + 2, 4), nullptr, 16);
                    i += 6;
                    code = 0x10000 + ((code - 0xd800) << 10) + (low - 0xdc00);
                }
                if (code < 0x80) out += static_cast<char>(code);
                else if (code < 0x800) {
                    out += static_cast<char>(0xc0 | (code >> 6));
                    out += static_cast<char>(0x80 | (code & 0x3f));
                } else if (code < 0x10000) {
                    out += static_cast<char>(0xe0 | (code >> 12));
                    out += static_cast<char>(0x80 | ((code >> 6) & 0x3f));
                    out += static_cast<char>(0x80 | (code & 0x3f));
                } else {
                    out += static_cast<char>(0xf0 | (code >> 18));
                    out += static_cast<char>(0x80 | ((code >> 12) & 0x3f));
                    out += static_cast<char>(0x80 | ((code >> 6) & 0x3f));
                    out += static_cast<char>(0x80 | (code & 0x3f));
                }
            } else out += e;
        }
        i++;  // closing quote
        return out;
    }

    Json value() {
        space();
        Json v;
        char c = s[i];
        if (c == '[') {
            v.kind = Json::Array;
            i++;
            space();
            if (s[i] == ']') {
                i++;
                return v;
            }
            while (true) {
                v.items.push_back(value());
                space();
                if (s[i++] == ']') return v;
            }
        }
        if (c == '{') {
            v.kind = Json::Object;
            i++;
            space();
            if (s[i] == '}') {
                i++;
                return v;
            }
            while (true) {
                space();
                std::string key = string();
                space();
                i++;  // ':'
                v.fields.emplace_back(key, value());
                space();
                if (s[i++] == '}') return v;
            }
        }
        if (c == '"') {
            v.kind = Json::String;
            v.text = string();
            return v;
        }
        if (s.compare(i, 4, "true") == 0 || s.compare(i, 5, "false") == 0) {
            v.kind = Json::Bool;
            v.boolean = s[i] == 't';
            i += v.boolean ? 4 : 5;
            return v;
        }
        if (s.compare(i, 4, "null") == 0) {
            i += 4;
            return v;
        }
        size_t start = i;
        while (i < s.size() && std::string("+-0123456789.eE").find(s[i]) != std::string::npos) i++;
        std::string num = s.substr(start, i - start);
        v.kind = Json::Number;
        v.number = std::strtod(num.c_str(), nullptr);
        v.integer = num.find_first_of(".eE") == std::string::npos ? std::strtoll(num.c_str(), nullptr, 10)
                                                                  : static_cast<long long>(v.number);
        return v;
    }
};

inline Json parse(const std::string& text) {
    Parser p{text};
    return p.value();
}

// -- JSON to the method's argument types ----------------------------------------------------
template <class T, class = void>
struct Decode;

template <class T>
T from_json(const Json& j) {
    return Decode<T>::get(j);
}

template <class T>
struct Decode<T, std::enable_if_t<std::is_integral_v<T> && !std::is_same_v<T, bool>>> {
    static T get(const Json& j) { return static_cast<T>(j.integer); }
};
template <class T>
struct Decode<T, std::enable_if_t<std::is_floating_point_v<T>>> {
    static T get(const Json& j) { return static_cast<T>(j.number); }
};
template <>
struct Decode<bool> {
    static bool get(const Json& j) { return j.boolean; }
};
template <>
struct Decode<std::string> {
    static std::string get(const Json& j) { return j.text; }
};
template <class T>
struct Decode<std::vector<T>> {
    static std::vector<T> get(const Json& j) {
        std::vector<T> out;
        out.reserve(j.items.size());
        for (const auto& x : j.items) out.push_back(from_json<T>(x));
        return out;
    }
};
template <class T>
struct Decode<std::optional<T>> {
    static std::optional<T> get(const Json& j) {
        if (j.kind == Json::Null) return std::nullopt;
        return from_json<T>(j);
    }
};
template <class A, class B>
struct Decode<std::pair<A, B>> {
    static std::pair<A, B> get(const Json& j) { return {from_json<A>(j[0]), from_json<B>(j[1])}; }
};
template <class... T>
struct Decode<std::tuple<T...>> {
    template <size_t... I>
    static std::tuple<T...> make(const Json& j, std::index_sequence<I...>) {
        return std::tuple<T...>(from_json<T>(j[I])...);
    }
    static std::tuple<T...> get(const Json& j) { return make(j, std::index_sequence_for<T...>{}); }
};

#ifdef SWE_LISTNODE
template <>
struct Decode<ListNode*> {
    static ListNode* get(const Json& j) {
        ListNode* head = nullptr;
        for (size_t i = j.items.size(); i-- > 0;) head = new ListNode(static_cast<int>(j.items[i].integer), head);
        return head;
    }
};
#endif

#ifdef SWE_TREENODE
template <>
struct Decode<TreeNode*> {
    // The usual level order: [1, null, 2, 3] is 1 with right child 2, whose left is 3.
    static TreeNode* get(const Json& j) {
        const auto& v = j.items;
        if (v.empty() || v[0].kind == Json::Null) return nullptr;
        TreeNode* root = new TreeNode(static_cast<int>(v[0].integer));
        std::queue<TreeNode*> queue;
        queue.push(root);
        size_t i = 1;
        while (!queue.empty() && i < v.size()) {
            TreeNode* parent = queue.front();
            queue.pop();
            if (i < v.size() && v[i].kind != Json::Null) {
                parent->left = new TreeNode(static_cast<int>(v[i].integer));
                queue.push(parent->left);
            }
            i++;
            if (i < v.size() && v[i].kind != Json::Null) {
                parent->right = new TreeNode(static_cast<int>(v[i].integer));
                queue.push(parent->right);
            }
            i++;
        }
        return root;
    }
};
#endif

#ifdef SWE_GRAPHNODE
template <>
struct Decode<Node*> {
    // Node i+1's neighbors are j[i]; returns node 1, or nullptr for an empty graph.
    static Node* get(const Json& j) {
        std::vector<Node*> nodes;
        for (size_t i = 0; i < j.size(); i++) nodes.push_back(new Node(static_cast<int>(i + 1)));
        for (size_t i = 0; i < j.size(); i++)
            for (const auto& w : j[i].items) nodes[i]->neighbors.push_back(nodes[w.integer - 1]);
        return nodes.empty() ? nullptr : nodes[0];
    }
};

inline std::vector<Node*> graph_nodes(Node* start, std::string* error = nullptr) {
    std::vector<Node*> out;
    std::unordered_set<Node*> seen;
    std::queue<Node*> queue;
    if (start) queue.push(start);
    while (!queue.empty()) {
        Node* n = queue.front();
        queue.pop();
        if (!n || !seen.insert(n).second) continue;
        if (seen.size() > MAX_NODES) {
            if (error) *error = "The graph is too large.";
            break;
        }
        out.push_back(n);
        for (Node* w : n->neighbors) queue.push(w);
    }
    return out;
}
#endif

// -- results to JSON --------------------------------------------------------------------------
struct Writer {
    std::string out;
    bool pretty = false;
    std::string error;  // a malformed list, tree or graph: why

    const char* sep() const { return pretty ? ", " : ","; }
};

inline void write_string(Writer& w, const std::string& s) {
    w.out += '"';
    for (unsigned char c : s) {
        if (c == '"') w.out += "\\\"";
        else if (c == '\\') w.out += "\\\\";
        else if (c == '\n') w.out += "\\n";
        else if (c == '\r') w.out += "\\r";
        else if (c == '\t') w.out += "\\t";
        else if (c < 0x20) {
            char buf[8];
            std::snprintf(buf, sizeof buf, "\\u%04x", c);
            w.out += buf;
        } else w.out += static_cast<char>(c);
    }
    w.out += '"';
}

// Every overload is declared before the templates that call them.
inline void write(Writer& w, bool v);
inline void write(Writer& w, char v);
inline void write(Writer& w, const std::string& v);
inline void write(Writer& w, const char* v);
inline void write(Writer& w, std::nullopt_t);
inline void write(Writer& w, std::nullptr_t);
template <class T>
std::enable_if_t<std::is_integral_v<T> && !std::is_same_v<T, bool> && !std::is_same_v<T, char>> write(Writer& w, T v);
template <class T>
std::enable_if_t<std::is_floating_point_v<T>> write(Writer& w, T v);
template <class T>
void write(Writer& w, const std::vector<T>& v);
template <class T>
void write(Writer& w, const std::optional<T>& v);
template <class A, class B>
void write(Writer& w, const std::pair<A, B>& v);
template <class... T>
void write(Writer& w, const std::tuple<T...>& v);
#ifdef SWE_LISTNODE
inline void write(Writer& w, ListNode* head);
#endif
#ifdef SWE_TREENODE
inline void write(Writer& w, TreeNode* root);
#endif
#ifdef SWE_GRAPHNODE
inline void write(Writer& w, Node* start);
#endif

inline void write(Writer& w, bool v) { w.out += v ? "true" : "false"; }
inline void write(Writer& w, char v) { write_string(w, std::string(1, v)); }
inline void write(Writer& w, const std::string& v) { write_string(w, v); }
inline void write(Writer& w, const char* v) { write_string(w, v ? v : ""); }
inline void write(Writer& w, std::nullopt_t) { w.out += "null"; }
inline void write(Writer& w, std::nullptr_t) { w.out += "null"; }

template <class T>
std::enable_if_t<std::is_integral_v<T> && !std::is_same_v<T, bool> && !std::is_same_v<T, char>> write(Writer& w, T v) {
    w.out += std::to_string(v);
}

template <class T>
std::enable_if_t<std::is_floating_point_v<T>> write(Writer& w, T v) {
    if (!std::isfinite(v)) {
        w.out += w.pretty ? (std::isnan(v) ? "nan" : (v > 0 ? "inf" : "-inf")) : "null";
        return;
    }
    char buf[32];
    std::snprintf(buf, sizeof buf, "%.17g", static_cast<double>(v));
    std::string text = buf;
    if (text.find_first_of(".eE") == std::string::npos) text += ".0";
    w.out += text;
}

template <class T>
void write(Writer& w, const std::vector<T>& v) {
    w.out += '[';
    bool first = true;
    for (const auto& x : v) {
        if (!first) w.out += w.sep();
        first = false;
        write(w, static_cast<const T&>(x));
    }
    w.out += ']';
}

template <class T>
void write(Writer& w, const std::optional<T>& v) {
    if (v) write(w, *v);
    else w.out += "null";
}

template <class A, class B>
void write(Writer& w, const std::pair<A, B>& v) {
    w.out += '[';
    write(w, v.first);
    w.out += w.sep();
    write(w, v.second);
    w.out += ']';
}

template <class... T>
void write(Writer& w, const std::tuple<T...>& v) {
    w.out += '[';
    size_t i = 0;
    std::apply([&](const auto&... x) { ((w.out += (i++ ? w.sep() : ""), write(w, x)), ...); }, v);
    w.out += ']';
}

#ifdef SWE_LISTNODE
inline void write(Writer& w, ListNode* head) {
    std::unordered_set<ListNode*> seen;
    std::vector<int> values;
    for (ListNode* n = head; n; n = n->next) {
        if (!seen.insert(n).second) {
            w.error = "The linked list loops back on itself (it has a cycle).";
            return;
        }
        if (values.size() >= MAX_NODES) {
            w.error = "The linked list is too long.";
            return;
        }
        values.push_back(n->val);
    }
    write(w, values);
}
#endif

#ifdef SWE_TREENODE
inline void write(Writer& w, TreeNode* root) {
    if (!root) {
        w.out += "[]";
        return;
    }
    std::vector<std::optional<int>> values;
    std::unordered_set<TreeNode*> seen;
    std::vector<TreeNode*> queue{root};
    for (size_t k = 0; k < queue.size(); k++) {
        TreeNode* n = queue[k];
        if (!n) {
            values.push_back(std::nullopt);
            continue;
        }
        if (!seen.insert(n).second) {
            w.error = "That isn't a tree: a node is reachable twice.";
            return;
        }
        if (seen.size() > MAX_NODES) {
            w.error = "The tree is too large.";
            return;
        }
        values.push_back(n->val);
        queue.push_back(n->left);
        queue.push_back(n->right);
    }
    while (!values.empty() && !values.back()) values.pop_back();
    write(w, values);
}
#endif

#ifdef SWE_GRAPHNODE
inline void write(Writer& w, Node* start) {
    std::vector<Node*> nodes = graph_nodes(start, &w.error);
    if (!w.error.empty()) return;
    std::unordered_map<int, Node*> by_val;
    for (Node* n : nodes) {
        if (!by_val.emplace(n->val, n).second) {
            w.error = "Two nodes have the value " + std::to_string(n->val) + ".";
            return;
        }
    }
    for (size_t v = 1; v <= nodes.size(); v++) {
        if (!by_val.count(static_cast<int>(v))) {
            w.error = "Node values must be 1..n, like the input's.";
            return;
        }
    }
    std::vector<std::vector<int>> rows;
    for (size_t v = 1; v <= nodes.size(); v++) {
        std::vector<int> row;
        for (Node* x : by_val[static_cast<int>(v)]->neighbors) row.push_back(x ? x->val : 0);
        rows.push_back(row);
    }
    write(w, rows);
}
#endif

/** A value as the tests write it, for people: [1, 2], "text", null, true. */
template <class T>
std::string show(const T& value) {
    Writer w;
    w.pretty = true;
    write(w, value);
    return w.error.empty() ? w.out : "<" + w.error + ">";
}

// -- the test loop -------------------------------------------------------------------------------
inline int emit(const std::string& event) {
    std::cout.flush();
    std::cerr.flush();
    std::fflush(stdout);
    std::fflush(stderr);
    return swe_emit(event.data(), static_cast<int>(event.size()));
}

inline std::string quote(const std::string& s) {
    Writer w;
    write_string(w, s);
    return w.out;
}

/** One test step: the harness calls one of these around the solution's method. */
struct Step {
    bool stop = false;

    using Clock = std::chrono::steady_clock;

    static double ms_since(Clock::time_point t0) {
        return std::chrono::duration<double, std::milli>(Clock::now() - t0).count();
    }

    void finish(double ms, const Writer& w) {
        std::string event = w.error.empty()
            ? "{\"e\":\"step\",\"ms\":" + std::to_string(ms) + ",\"value\":" + w.out + "}"
            : "{\"e\":\"step\",\"adapter\":" + quote(w.error) + "}";
        if (!emit(event)) stop = true;
    }

    /** Call f() and report what it returns. */
    template <class F>
    void call(F f) {
        emit("{\"e\":\"call\"}");
        Writer w;
        auto t0 = Clock::now();
        if constexpr (std::is_void_v<decltype(f())>) {
            f();
            double ms = ms_since(t0);
            w.out = "null";
            finish(ms, w);
        } else {
            auto result = f();
            double ms = ms_since(t0);
            write(w, result);
            finish(ms, w);
        }
    }

    /** Call f() (an in-place method), then report what after(w) writes: the changed argument. */
    template <class F, class G>
    void call(F f, G after) {
        emit("{\"e\":\"call\"}");
        auto t0 = Clock::now();
        f();
        double ms = ms_since(t0);
        Writer w;
        after(w);
        finish(ms, w);
    }

#ifdef SWE_GRAPHNODE
    /** Call f(), which must return a copy of the graph that shares none of `originals`. */
    template <class F>
    void call_graph_copy(F f, const std::vector<Node*>& originals) {
        emit("{\"e\":\"call\"}");
        auto t0 = Clock::now();
        Node* result = f();
        double ms = ms_since(t0);
        Writer w;
        std::unordered_set<Node*> old(originals.begin(), originals.end());
        for (Node* n : graph_nodes(result, &w.error)) {
            if (old.count(n)) {
                w.error = "The copy reuses nodes of the original graph: clone every node.";
                break;
            }
        }
        if (w.error.empty()) write(w, result);
        finish(ms, w);
    }
#endif

    void unknown(const std::string& name) {
        Writer w;
        w.error = "The tests call an unknown method: " + name;
        finish(0, w);
    }
};

template <class T, class F>
int run(F step_fn) {
    std::string input((std::istreambuf_iterator<char>(std::cin)), std::istreambuf_iterator<char>());
    Json data = parse(input);
    for (const Json& test : data.get("tests").items) {
        emit("{\"e\":\"start\"}");
        T* self = new T();  // never freed: each test gets a fresh one, and the run is short
        for (const Json& step : test.get("steps").items) {
            Step s;
            step_fn(*self, step.get("call").text, step.get("args"), s);
            if (s.stop) break;
        }
        emit("{\"e\":\"end\"}");
    }
    emit("{\"e\":\"done\"}");
    return 0;
}

}  // namespace swe
