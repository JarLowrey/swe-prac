from collections import Counter


class Solution:
    def minWindow(self, s: str, t: str) -> str:
        # need[c]: how many more c's the window needs. Positive = still missing, 0 = exactly
        # enough, negative = spare copies (or a character t doesn't contain at all).
        need = Counter(t)
        # The total of the positive need values: the window covers t exactly when it is 0.
        # Tracking it saves comparing every count at every step.
        missing = len(t)
        best_start, best_len = 0, len(s) + 1  # longer than any real window means "none yet"
        left = 0
        for right, c in enumerate(s):
            # Grow: s[right] enters the window.
            if need[c] > 0:
                missing -= 1  # a character we still needed, not a spare
            need[c] -= 1
            # Shrink while the window still covers t; each of these windows is a candidate.
            # Both pointers only move forwards, so the whole loop is O(len(s)).
            while missing == 0:
                if right - left + 1 < best_len:
                    best_start, best_len = left, right - left + 1
                need[s[left]] += 1  # s[left] leaves the window
                if need[s[left]] > 0:
                    missing += 1  # it was needed: the window no longer covers t
                left += 1
        # Slice once at the end, and only if a window was found.
        return s[best_start : best_start + best_len] if best_len <= len(s) else ""
