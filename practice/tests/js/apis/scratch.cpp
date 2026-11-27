// The parts of C++'s standard library and language that interview code uses, run as a scratch
// file on the site's clang (solutions.test.mjs). Each check prints "ok <name>" or
// "FAIL <name>: ...".
#include <bits/stdc++.h>
#include <regex>
using namespace std;

static int passed = 0, failed = 0;

template <class A, class B>
void check(const string& name, const A& got, const B& want) {
    if (got == want) {
        passed++;
        cout << "ok " << name << "\n";
        return;
    }
    failed++;
    cout << "FAIL " << name;
    if constexpr (requires { cout << got << want; }) cout << ": got " << got << ", want " << want;
    cout << "\n";
}

template <class T>
string str(T&& items) {
    ostringstream out;
    out << "[";
    for (bool first = true; const auto& x : items) {
        out << (first ? "" : ", ") << x;
        first = false;
    }
    out << "]";
    return out.str();
}

struct Point {
    int x, y;
    auto operator<=>(const Point&) const = default;
};

int fib(int n, vector<int>& memo) {
    if (n < 2) return n;
    if (memo[n]) return memo[n];
    return memo[n] = fib(n - 1, memo) + fib(n - 2, memo);
}

int main() {
    // Algorithms
    vector<int> v = {5, 3, 8, 1, 3};
    sort(v.begin(), v.end());
    check("sort", str(v), string("[1, 3, 3, 5, 8]"));
    sort(v.begin(), v.end(), greater<int>());
    check("sort greater", str(v), string("[8, 5, 3, 3, 1]"));
    sort(v.begin(), v.end());
    check("bounds", (lower_bound(v.begin(), v.end(), 3) - v.begin()) * 10 + (upper_bound(v.begin(), v.end(), 3) - v.begin()), 13L);
    check("binary_search", binary_search(v.begin(), v.end(), 5), true);
    v.erase(unique(v.begin(), v.end()), v.end());
    check("unique", str(v), string("[1, 3, 5, 8]"));
    vector<int> perm = {1, 2, 3};
    int perms = 0;
    do perms++;
    while (next_permutation(perm.begin(), perm.end()));
    check("next_permutation", perms, 6);
    vector<int> seq(5);
    iota(seq.begin(), seq.end(), 1);
    check("iota accumulate", accumulate(seq.begin(), seq.end(), 0LL), 15LL);
    vector<int> sums(5);
    partial_sum(seq.begin(), seq.end(), sums.begin());
    check("partial_sum", str(sums), string("[1, 3, 6, 10, 15]"));
    check("gcd lcm", gcd(12, 18) * 1000 + lcm(4, 6), 6012);
    check("GCC __gcd __lg", __gcd(12, 18) * 100 + __lg(8) * 10 + __lg(1000LL), 639);
    check("min max element", *min_element(seq.begin(), seq.end()) * 10 + *max_element(seq.begin(), seq.end()), 15);
    check("count_if", count_if(seq.begin(), seq.end(), [](int x) { return x % 2 == 0; }), 2L);
    vector<int> nth = {9, 1, 7, 3, 5};
    nth_element(nth.begin(), nth.begin() + 2, nth.end());
    check("nth_element", nth[2], 5);
    rotate(seq.begin(), seq.begin() + 2, seq.end());
    check("rotate", str(seq), string("[3, 4, 5, 1, 2]"));
    reverse(seq.begin(), seq.end());
    check("reverse", seq.front(), 2);
    check("ranges", str(views::iota(0, 6) | views::filter([](int x) { return x % 2 == 0; }) | views::transform([](int x) { return x * x; })), string("[0, 4, 16]"));
    vector<int> r = {3, 1, 2};
    ranges::sort(r);
    check("ranges::sort", str(r) + to_string(ranges::max(r)), string("[1, 2, 3]3"));
    check("popcount", __builtin_popcount(255) + popcount(7u) + bit_width(8u), 15);

    // Containers
    map<string, int> counts;
    for (string w : {"a", "b", "a", "c", "a"}) counts[w]++;
    string seen;
    for (const auto& [word, n] : counts) seen += word + to_string(n);
    check("map structured bindings", seen, string("a3b1c1"));
    check("map contains", counts.contains("b") && !counts.contains("z"), true);
    map<int, string> tree = {{10, "a"}, {20, "b"}, {30, "c"}};
    check("map bounds", prev(tree.upper_bound(25))->first * 100 + tree.lower_bound(11)->first + tree.rbegin()->first, 2050);
    multiset<int> ms = {1, 2, 2, 3};
    ms.erase(ms.find(2));
    check("multiset", ms.count(2) * 10 + ms.size(), 13UL);
    set<int> s = {5, 1, 9};
    check("set", *s.begin() * 10 + *prev(s.end()), 19);
    unordered_map<int, int> hm;
    hm[3] += 2;
    check("unordered_map", hm.count(3) + hm[3] + hm.size(), 4UL);
    unordered_set<string> us = {"x"};
    check("unordered_set", us.count("x") + us.count("y"), 1UL);
    priority_queue<int> maxHeap;
    for (int x : {3, 7, 5}) maxHeap.push(x);
    priority_queue<pair<int, int>, vector<pair<int, int>>, greater<>> minHeap;
    minHeap.push({2, 1});
    minHeap.push({1, 9});
    check("priority_queue", maxHeap.top() * 10 + minHeap.top().second, 79);
    deque<int> dq;
    dq.push_back(1);
    dq.push_front(0);
    dq.pop_back();
    stack<int> st;
    st.push(4);
    queue<int> q;
    q.push(6);
    check("deque stack queue", dq.front() + st.top() + q.front(), 10);
    bitset<8> bits("1011");
    check("bitset", bits.count() * 100 + bits.to_ulong(), 311UL);
    vector<vector<int>> grid(2, vector<int>(3, 0));
    grid[1][2] = 7;
    check("2d vector", grid[1][2] + grid[0].size(), 10UL);
    array<int, 3> arr{};
    arr.fill(4);
    check("array", accumulate(arr.begin(), arr.end(), 0), 12);
    map<pair<int, int>, int> byPair;
    byPair[{1, 2}] = 3;
    check("pair keys", byPair[make_pair(1, 2)], 3);
    tuple<int, string, double> t = {1, "two", 3.0};
    auto [one, two, three] = t;
    check("tuple", to_string(one) + two + to_string(get<2>(t)).substr(0, 3), string("1two3.0"));
    check("optional", optional<int>().value_or(-1) + optional<int>(5).value(), 4);
    check("spaceship", Point{1, 2} < Point{1, 3} && Point{2, 0} == Point{2, 0}, true);

    // Strings
    string text = "hello world";
    check("substr find", text.substr(6) + to_string(text.find('o')) + to_string(text.rfind('o')) + (text.find("zz") == string::npos ? "!" : "?"), string("world47!"));
    check("stoi to_string", stoi("-42") + stoll("10000000000"), 9999999958LL);
    check("starts ends with", text.starts_with("he") && text.ends_with("ld"), true);
    string upper = text;
    transform(upper.begin(), upper.end(), upper.begin(), ::toupper);
    check("toupper", upper, string("HELLO WORLD"));
    istringstream words("a b  c");
    vector<string> parts;
    for (string w; words >> w;) parts.push_back(w);
    check("split on spaces", str(parts), string("[a, b, c]"));
    istringstream csv("x,y,,z");
    parts.clear();
    for (string cell; getline(csv, cell, ',');) parts.push_back(cell);
    check("split on commas", str(parts), string("[x, y, , z]"));
    check("char math", string(3, 'x') + char('a' + 2), string("xxxc"));
    check("isdigit isalpha", isdigit('7') && isalpha('q') && tolower('Q') == 'q', true);
    string_view view = text;
    check("string_view", view.substr(0, 5) == "hello", true);
    ostringstream fixed2;
    fixed2 << fixed << setprecision(2) << 3.14159;
    check("setprecision", fixed2.str(), string("3.14"));
    check("format", format("{}-{:>3}-{:.1f}", 7, "x", 2.25), string("7-  x-2.2"));
    smatch found;
    string digits = "x12y345";
    check("regex", regex_search(digits, found, regex("\\d{3}")) && found.str() == "345", true);

    // Numbers and language
    check("division", to_string(-7 / 2) + to_string(-7 % 3), string("-3-1"));
    check("limits", INT_MAX == numeric_limits<int>::max() && LLONG_MAX > INT_MAX, true);
    check("long long math", 1LL * 100000 * 100000, 10000000000LL);
    __int128 big = 1;
    for (int i = 0; i < 100; i++) big *= 2;
    check("int128", (long long)(big >> 90), 1024LL);
    function<int(int)> fact = [&](int n) { return n <= 1 ? 1 : n * fact(n - 1); };
    auto add = [](auto a, auto b) { return a + b; };
    check("lambdas", fact(5) + add(1, 2), 123);
    vector<int> memo(50);
    check("recursion with memo", fib(40, memo), 102334155);
    vector<pair<string, int>> people = {{"b", 2}, {"a", 2}, {"c", 1}};
    sort(people.begin(), people.end(), [](const auto& x, const auto& y) { return x.second != y.second ? x.second > y.second : x.first < y.first; });
    check("sort with comparator", people[0].first + people[2].first, string("ac"));
    int deep = 0;
    vector<int> stackDepth(3000);
    function<void(int)> dive = [&](int n) { if (n < 3000) { stackDepth[n] = n; deep = n; dive(n + 1); } };
    dive(0);
    check("recursion 3000 deep", deep, 2999);
    printf("printf %d %s\n", 1, "two");
    cout << passed << " passed, " << failed << " failed" << endl;
    return 0;
}
