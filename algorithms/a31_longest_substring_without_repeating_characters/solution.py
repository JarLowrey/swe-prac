class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        # A sliding window s[start..end] that never contains a repeated character.
        # last_seen remembers where each character last appeared (anywhere, not only inside
        # the window), so on a repeat we can jump start straight past the earlier copy.
        last_seen: dict[str, int] = {}
        start = 0
        best = 0
        for end, c in enumerate(s):
            # Only a copy at or after start is inside the window. An older one ("abba": the
            # first a, seen again at the end) is already outside, and start must not go back.
            if last_seen.get(c, -1) >= start:
                start = last_seen[c] + 1
            last_seen[c] = end
            best = max(best, end - start + 1)  # + 1: start == end is one character
        return best
