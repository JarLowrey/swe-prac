// <bits/stdc++.h>: every standard header a solution is likely to use, as GCC's version gives.
// This toolchain's standard library (libc++) has no such header, so the site provides one. It's
// also what the site precompiles, so including it costs nothing.
#pragma once

#include <cassert>
#include <cctype>
#include <cfloat>
#include <cinttypes>
#include <climits>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>

#include <algorithm>
#include <array>
#include <bit>
#include <bitset>
#include <chrono>
#include <compare>
#include <complex>
#include <concepts>
#include <deque>
#include <forward_list>
#include <functional>
#include <initializer_list>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <limits>
#include <list>
#include <map>
#include <memory>
#include <numbers>
#include <numeric>
#include <optional>
#include <queue>
#include <random>
#include <ranges>
#include <set>
#include <span>
#include <sstream>
#include <stack>
#include <string>
#include <string_view>
#include <tuple>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <variant>
#include <vector>

// Two of GCC's own helpers that solutions written for it use: __gcd (std::gcd is the standard
// one) and __lg, the floor of log2 of a positive n.
namespace std {
template <class T>
constexpr T __gcd(T m, T n) {
    while (n != 0) {
        T rest = m % n;
        m = n;
        n = rest;
    }
    return m;
}
constexpr int __lg(int n) { return 31 - __builtin_clz(n); }
constexpr int __lg(unsigned n) { return 31 - __builtin_clz(n); }
constexpr int __lg(long n) { return 8 * sizeof(long) - 1 - __builtin_clzl(n); }
constexpr int __lg(unsigned long n) { return 8 * sizeof(long) - 1 - __builtin_clzl(n); }
constexpr int __lg(long long n) { return 63 - __builtin_clzll(n); }
constexpr int __lg(unsigned long long n) { return 63 - __builtin_clzll(n); }
}  // namespace std
