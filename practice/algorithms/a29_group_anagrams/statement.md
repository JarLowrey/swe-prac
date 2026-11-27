Given an array of strings `strs`, group the words that are anagrams of each other. Return the
groups in any order; the words inside a group can be in any order too.

Two words are anagrams if one is a rearrangement of the other: the same letters, each the same
number of times.

**Example 1**

```
Input:  strs = ["eat", "tea", "tan", "ate", "nat", "bat"]
Output: [["bat"], ["nat", "tan"], ["ate", "eat", "tea"]]
```

"eat", "tea" and "ate" use the letters a, e and t once each; "tan" and "nat" use a, n and t; "bat"
has no anagram in the list.

```grid
rowlabels: word sorted
eat tea tan ate nat bat
aet aet ant aet ant abt
highlight: 1,0 1,1 1,3
caption: eat, tea and ate sort to the same letters: one group
```

**Example 2**

```
Input:  strs = [""]
Output: [[""]]
```

The empty string is a group of one.

**Example 3**

```
Input:  strs = ["ab", "ba", "aba"]
Output: [["ab", "ba"], ["aba"]]
```

"aba" has the same letters as "ab", but two a's instead of one, so it is not an anagram of it.

**Constraints**

- `0 <= len(strs) <= 10^4`
- `0 <= len(strs[i]) <= 100`
- Every string consists of lowercase English letters.
