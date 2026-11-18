**Hint 1.** Trying every rearrangement of `s` is n! work. All that matters about each string here
is which letters it contains and how many of each. Two strings of different lengths can never be
anagrams.

**Hint 2.** Sorting both strings gives O(n log n): anagrams sort to the same string.

**Hint 3.** For O(n), count the letters of each string with a dict (or an array of 26 counts) and
compare the counts.

**Hint 4.** One table is enough: add 1 for each letter of `s`, then subtract 1 for each letter of
`t`. If the lengths are equal and no count is ever asked to go below zero, every count ends at
zero, so the strings are anagrams.
