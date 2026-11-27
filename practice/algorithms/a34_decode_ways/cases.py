"""Tests for Decode Ways. Expected outputs come from solution.py, checked against brute()."""

import random

SHOWN = [
    {"name": "Example 1", "args": ("12",), "expect": 2},
    {"name": "Example 2", "args": ("226",), "expect": 3},
    {"name": "Example 3", "args": ("106",), "expect": 1},
    {"name": "Example 4", "args": ("06",), "expect": 0},
]

# 100 digits with 12 zeros and about a billion decodings (found by a seeded search; the answer
# fits in 32 bits). The plain recursion makes at least one call per decoding.
BILLION = (
    "2925106121522652261122581991711102105122121203220201024221115110512011620952220420174112"
    "752712241148"
)

HIDDEN = [
    {"name": "a lone zero", "args": ("0",), "expect": 0},
    {"name": "one digit", "args": ("1",), "expect": 1},
    {"name": "10 must stay together", "args": ("10",), "expect": 1},
    {"name": "27 is not a letter", "args": ("27",), "expect": 1},
    {"name": "two zeros in a row", "args": ("100",), "expect": 0},
    {"name": "zero in the middle", "args": ("101",), "expect": 1},
    {"name": "1 23 is easy to miss", "args": ("123",), "expect": 3},
    {"name": "a zero cuts off a choice", "args": ("11106",), "expect": 2},
    {"name": "30 is not a letter", "args": ("301",), "expect": 0},
    {"name": "only 2 10 1 works", "args": ("2101",), "expect": 1},
    {"name": "ten 1s", "args": ("1111111111",), "expect": 89},
    {"name": "sixteen digits", "args": ("2611055971756562",), "expect": 4},
    {
        "name": "100 digits, a billion decodings",
        "args": (BILLION,),
        "expect": 1051315200,
        "limit_ms": 500,
    },
    # Every path through the 1s reaches the 00 and fails: zeros must be memoized too.
    {"name": "98 ones and 00", "args": ("1" * 98 + "00",), "expect": 0, "limit_ms": 500},
]

CODES = {str(k) for k in range(1, 27)}  # "1" .. "26": the only valid groups


def brute(s):
    """Try every way to cut the string (a bit mask of cut positions) and keep the cuts whose
    pieces are all letter codes (small inputs only)."""
    n = len(s)
    count = 0
    for mask in range(1 << (n - 1)):
        pieces, start = [], 0
        for gap in range(n - 1):
            if mask >> gap & 1:
                pieces.append(s[start : gap + 1])
                start = gap + 1
        pieces.append(s[start:])
        if all(p in CODES for p in pieces):
            count += 1
    return count


def naive(s):
    """The plain recursion without a memo: exponential, so the large tests must reject it."""

    def ways(i):
        if i == len(s):
            return 1
        if s[i] == "0":
            return 0
        total = ways(i + 1)
        if i + 1 < len(s) and "10" <= s[i : i + 2] <= "26":
            total += ways(i + 2)
        return total

    return ways(0)


def random_cases(rng: random.Random):
    for _ in range(300):
        n = rng.randint(1, 12)
        yield ("".join(rng.choice("00111222345679") for _ in range(n)),)
