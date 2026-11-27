class Solution:
    def longestPalindrome(self, s: str) -> str:
        # Every palindrome grows outwards from its center, so try every center instead of
        # every substring. Keep the best as indices: slicing inside the loop would copy
        # characters on every step.
        start, end = 0, 0  # the best palindrome so far is s[start:end]
        for i in range(len(s)):
            # Odd lengths are centered on s[i] ("aba"); even lengths on the gap after it ("abba").
            for lo, hi in (self.expand(s, i, i), self.expand(s, i, i + 1)):
                if hi - lo > end - start:
                    start, end = lo, hi
        return s[start:end]

    def expand(self, s: str, lo: int, hi: int) -> tuple[int, int]:
        """Grow s[lo..hi] outwards while both ends match. Returns the half-open range
        [lo, hi) of the longest palindrome around this center (empty if s[lo] != s[hi])."""
        while lo >= 0 and hi < len(s) and s[lo] == s[hi]:
            lo -= 1
            hi += 1
        # The loop stops one step past the palindrome on each side.
        return lo + 1, hi
