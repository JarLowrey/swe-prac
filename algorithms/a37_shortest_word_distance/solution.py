class Solution:
    def shortestDistance(self, wordsDict: list[str], word1: str, word2: str) -> int:
        # The closest pair has no other copy of either word between them (that copy would make
        # a closer pair), so only consecutive occurrences need comparing. One pass, remembering
        # just the index of the most recent word1 or word2.
        last = -1  # -1: neither word seen yet
        best = len(wordsDict)  # larger than any real distance
        for i, word in enumerate(wordsDict):
            if word in (word1, word2):
                # Check last first: wordsDict[-1] wouldn't fail, it would read the last word.
                if last != -1 and wordsDict[last] != word:
                    best = min(best, i - last)  # the other word, just before this one
                # Either way this occurrence becomes the latest: it is at least as close to
                # everything still to come as the older one.
                last = i
        return best
