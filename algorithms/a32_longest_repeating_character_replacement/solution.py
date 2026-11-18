from collections import Counter


class Solution:
    def characterReplacement(self, s: str, k: int) -> int:
        # A window works if we keep its most frequent letter and change the rest:
        # length - top count <= k.
        count: Counter[str] = Counter()  # letters in the window s[left..right]
        # The highest count any letter has reached in the window so far. It is never lowered:
        # a window longer than the best needs some letter to appear more than max_freq times,
        # and at that moment max_freq is updated to an exact count.
        max_freq = 0
        left = best = 0
        for right, c in enumerate(s):
            count[c] += 1
            max_freq = max(max_freq, count[c])  # only c's count went up
            if right - left + 1 - max_freq > k:
                # Too many changes for a longer window: slide instead of growing (left and
                # right both move one step), so the length stays at the best found so far.
                count[s[left]] -= 1
                left += 1
            best = max(best, right - left + 1)
        return best
