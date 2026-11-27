**Hint 1.** Comparing every word with every group (an anagram check each time) is O(n²) checks.
Instead, look for something you can compute from **one word alone** that comes out the same for
exactly its anagrams.

**Hint 2.** Sorting a word's letters works: "eat", "tea" and "ate" all sort to "aet". Use that as
a dictionary key, mapping to the list of words with that key. One pass groups everything.

**Hint 3.** Sorting costs O(m log m) for a word of length m. A word's letter counts are also the
same exactly for its anagrams, and counting takes O(m).

**Hint 4.** Lists can't be dictionary keys, but tuples can: `tuple(counts)` of the 26 counts is a
key. If you join the counts into a string instead, put a separator between them, or the counts
1, 11 and 11, 1 both become "111".
