class Solution:
    def wordBreak(self, s: str, wordDict: list[str]) -> bool:
        words = set(wordDict)  # O(1) average lookups instead of scanning a list
        lengths = sorted({len(w) for w in words})  # only these lengths can possibly be words
        n = len(s)

        # ok[i] is True when the rest of the string, s[i:], splits into words. Whatever words
        # came before position i, this is the only question left, so one index is the state.
        ok = [False] * (n + 1)
        ok[n] = True  # the empty rest is a complete split: the base case

        # Each ok[i] depends only on later positions, so fill from the end towards the front.
        for i in range(n - 1, -1, -1):
            for length in lengths:
                j = i + length
                if j > n:
                    break  # lengths are sorted: this one and all longer ones run past the end
                # s[i:j] is a word and the rest after it splits: then s[i:] splits.
                # Checking ok[j] first skips building the slice when the rest is hopeless.
                if ok[j] and s[i:j] in words:
                    ok[i] = True
                    break  # one way is enough
        return ok[0]
