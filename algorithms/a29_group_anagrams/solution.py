class Solution:
    def groupAnagrams(self, strs: list[str]) -> list[list[str]]:
        # Give every word a key that is the same exactly for its anagrams, then let a dict do the
        # grouping in one pass: no word is ever compared with another word.
        groups: dict[tuple[int, ...], list[str]] = {}
        for word in strs:
            # The key: how many times each letter a..z appears. Counting is O(len(word)), cheaper
            # than sorting the letters (O(m log m)), which would also make a valid key.
            counts = [0] * 26
            for ch in word:
                counts[ord(ch) - ord("a")] += 1
            # A list can't be a dict key, but a tuple can.
            groups.setdefault(tuple(counts), []).append(word)
        # Each dict value is one complete group (dicts keep insertion order, so the groups come
        # out in the order of their first word).
        return list(groups.values())
