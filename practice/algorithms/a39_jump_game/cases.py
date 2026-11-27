"""Tests for Jump Game. Expected outputs come from solution.py, checked against brute()."""

import random

SHOWN = [
    {"name": "Example 1", "args": ([2, 3, 1, 1, 4],), "expect": True},
    {"name": "Example 2", "args": ([3, 2, 1, 0, 4],), "expect": False},
    {"name": "Example 3", "args": ([0],), "expect": True},
]


def dead_end(n: int) -> list[int]:
    """[n-2, n-3, ..., 1, 0, 1]: every index reaches exactly the 0 just before the end, and no
    further: False. A DP or BFS that tries every jump does about n²/2 steps."""
    return list(range(n - 2, -1, -1)) + [1]


def staircase(n: int, trap: int) -> list[int]:
    """Index 0 can jump straight to trap + 1, where a path of 1s leads to the end: True. But
    indices 1..trap-1 all funnel into the 0 at index `trap`, and a DP that tries short jumps
    first explores every one of those jumps (~trap²/2 steps) before finding the long one."""
    return [trap + 1] + [trap - i for i in range(1, trap)] + [0] + [1] * (n - trap - 1)


HIDDEN = [
    {"name": "stuck at the start", "args": ([0, 1],), "expect": False},
    {"name": "one element", "args": ([5],), "expect": True},
    {"name": "a zero in the way", "args": ([1, 0, 1],), "expect": False},
    {"name": "jump over the zero", "args": ([2, 0, 1],), "expect": True},
    {"name": "the biggest jump is a trap", "args": ([3, 0, 5, 0, 0, 0],), "expect": True},
    {"name": "can't get to the big jump", "args": ([1, 0, 5, 0, 0, 0],), "expect": False},
    {"name": "one step at a time", "args": ([1, 1, 1, 1],), "expect": True},
    {"name": "a zero on the last index", "args": ([1, 1, 0],), "expect": True},
    {"name": "two zeros jumped at once", "args": ([2, 0, 0],), "expect": True},
    {"name": "a jump far past the end", "args": ([100_000, 0, 0, 0],), "expect": True},
    {"name": "a gap one step too wide", "args": ([1, 2, 0, 0, 1],), "expect": False},
    {"name": "unreachable big jump", "args": ([4, 0, 0, 0, 0, 1],), "expect": False},
    {"name": "big value early", "args": ([2, 5, 0, 0],), "expect": True},
    {
        "name": "15,000 elements, every route ends on a 0",
        "args": (dead_end(15_000),),
        "limit_ms": 500,
    },
    {
        "name": "15,000 elements, one long way round",
        "args": (staircase(15_000, 14_900),),
        "limit_ms": 500,
    },
]


def brute(nums):
    """Mark every index reachable from a reachable index, left to right."""
    reachable = [False] * len(nums)
    reachable[0] = True
    for i in range(len(nums)):
        if reachable[i]:
            for j in range(i + 1, min(len(nums), i + nums[i] + 1)):
                reachable[j] = True
    return reachable[-1]


def naive(nums):
    """The memoised recursion the large tests must reject: try every jump, shortest first.
    O(n²) in the worst case."""
    n = len(nums)
    memo = {}

    def can_finish(i):
        if i >= n - 1:
            return True
        if i not in memo:
            memo[i] = False
            for j in range(1, nums[i] + 1):
                if can_finish(i + j):
                    memo[i] = True
                    break
        return memo[i]

    return can_finish(0)


def random_cases(rng: random.Random):
    for _ in range(400):
        n = rng.randint(1, 10)
        # Plenty of zeros and small jumps, so both answers are common.
        yield ([rng.choice([0, 0, 1, 1, 2, 3, 4]) for _ in range(n)],)
