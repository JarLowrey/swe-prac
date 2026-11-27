class Solution:
    def numDecodings(self, s: str) -> int:
        # ways(i) = the number of ways to decode the suffix s[i:]. The next group is
        #   one digit:  s[i], valid for "1".."9"             -> ways(i + 1)
        #   two digits: s[i:i + 2], valid for "10".."26"     -> ways(i + 2)
        # and the two choices give different decodings, so their counts add up. A group never
        # starts with "0", so ways(i) = 0 when s[i] == "0". ways(n) = 1: nothing left to
        # decode is one complete decoding.
        #
        # Filling ways() from the end of the string to the front, each step reads only the next
        # two values, so two variables replace the table: O(n) time, O(1) space.
        n = len(s)
        after1, after2 = 1, 0  # ways(i + 1) and ways(i + 2), starting from ways(n) = 1
        for i in range(n - 1, -1, -1):
            if s[i] == "0":
                here = 0  # "0" alone isn't a letter, and "0x" isn't a code
            else:
                here = after1  # s[i] alone is a letter
                # Comparing two-digit strings works like comparing the numbers. (int() would
                # read "06" as 6 and accept it, but s[i] != "0" here anyway.)
                if i + 1 < n and "10" <= s[i : i + 2] <= "26":
                    here += after2  # s[i:i + 2] is a letter too
            after1, after2 = here, after1  # slide one position towards the front
        return after1  # ways(0): the whole string
