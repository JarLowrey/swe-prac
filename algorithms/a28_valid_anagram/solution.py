class Solution:
    def isAnagram(self, s: str, t: str) -> bool:
        # Anagrams have the same letter counts. Different lengths can't, and checking that first
        # is also what makes the single table below enough.
        if len(s) != len(t):
            return False

        # One table: +1 for each letter of s, then -1 for each letter of t. A dict works for any
        # characters (an array of 26 counts would only cover a to z).
        counts: dict[str, int] = {}
        for ch in s:
            counts[ch] = counts.get(ch, 0) + 1
        for ch in t:
            left = counts.get(ch, 0)
            if left == 0:
                return False  # t has more of ch than s does
            counts[ch] = left - 1

        # The counts started out summing to len(s) and t took away len(t) == len(s), without any
        # count going below zero: so every count is exactly zero.
        return True
