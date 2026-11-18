"""Tests for the Pair Sum fixture. Hidden case names start with "secret" so the tests can check
they never reach a session payload or the static site."""

SHOWN = [
    {"name": "Example 1", "args": ([2, 7, 11, 15], 9), "expect": [0, 1]},
    {"name": "Example 2", "args": ([3, 2, 4], 6), "expect": [1, 2]},
]

HIDDEN = [
    {"name": "secret negatives", "args": ([-3, 4, 3, 90], 0), "expect": [0, 2]},
    {"name": "secret duplicates", "args": ([3, 3], 6), "expect": [0, 1]},
    {"name": "secret far apart", "args": ([1, 5, 9, 4, 2], 10), "expect": [0, 2]},
]


def brute(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
    return []
