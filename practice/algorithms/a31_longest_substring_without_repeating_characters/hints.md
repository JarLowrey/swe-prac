**Hint 1.** The brute force checks every substring for repeats: O(n²) substrings, each O(n) to
check. Notice that once a substring from start `i` has a repeat, every longer one from `i` has it
too.

**Hint 2.** Keep a window `s[start..end]` that never contains a repeat. Move `end` forwards one
character at a time. When the new character is already inside the window, which starts can no
longer work?

**Hint 3.** Every start up to and including the earlier copy of that character now contains two
copies, so the window must start just after the earlier copy. `start` only ever moves forwards.

**Hint 4.** A dict from each character to the index where it was last seen tells you where the
earlier copy is in O(1). Careful: that copy may lie *before* `start` (try `"abba"`), and then it
is outside the window and must be ignored.
