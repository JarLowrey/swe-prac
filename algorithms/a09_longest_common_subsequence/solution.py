class Solution:
    def longestCommonSubsequence(self, text1: str, text2: str) -> int:
        # dp[i][j] = the LCS length of the suffixes text1[i:] and text2[j:]:
        #   text1[i] == text2[j]  ->  1 + dp[i + 1][j + 1]   (match them, move both)
        #   otherwise             ->  max(dp[i + 1][j], dp[i][j + 1])   (drop one, try both)
        # An empty suffix shares nothing, so the extra last row and column are 0.
        #
        # Row i reads only row i + 1 and itself, so we fill rows from the bottom up and keep
        # just two of them: O(m * n) time, O(min(m, n)) space.
        if len(text2) > len(text1):
            text1, text2 = text2, text1  # the answer is symmetric; make the rows the short side
        n = len(text2)
        below = [0] * (n + 1)  # row i + 1, starting with the all-zero empty-suffix row
        for i in range(len(text1) - 1, -1, -1):
            row = [0] * (n + 1)  # row i; row[n] = 0 is the empty-suffix column
            for j in range(n - 1, -1, -1):
                if text1[i] == text2[j]:
                    row[j] = 1 + below[j + 1]  # diagonal: both suffixes lose their first letter
                else:
                    row[j] = max(below[j], row[j + 1])  # below: drop text1[i]; right: drop text2[j]
            below = row
        return below[0]  # dp[0][0]: the whole strings
