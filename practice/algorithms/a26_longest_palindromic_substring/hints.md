**Hint 1.** Start with the brute force: there are about n²/2 substrings, and checking one takes
up to n steps, so it's O(n³). What work does it repeat? Checking `"xabax"` re-checks `"aba"`,
which was already a substring of its own.

**Hint 2.** `s[i..j]` is a palindrome exactly when `s[i] == s[j]` and the inside `s[i+1..j-1]` is
a palindrome. So palindromes grow outwards from their middle, one matching pair at a time.

**Hint 3.** Every palindrome has a center: a character (odd lengths, like `"aba"`) or the gap
between two characters (even lengths, like `"abba"`). A string of n characters has only 2n - 1
centers. From each one, how far can you grow?

**Hint 4.** Write a helper that takes `lo` and `hi`, moves them outwards while
`s[lo] == s[hi]`, and returns the range it reached. Call it with `(i, i)` and `(i, i + 1)` for
every `i`, keep the longest range as two indices, and slice once at the end.
