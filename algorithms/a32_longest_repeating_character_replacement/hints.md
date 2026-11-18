**Hint 1.** For one fixed substring, which letter should all the others become? How many changes
does that take, in terms of the substring's length and its letter counts?

**Hint 2.** Keep the most frequent letter and change the rest: a substring needs
`length - (count of its most frequent letter)` changes, so it works when that is at most `k`.
Shrinking a substring that works never breaks it, and growing one that doesn't never fixes it.

**Hint 3.** That is a sliding window. Move `right` forwards adding letters to a count table; when
`window length - top count > k`, move `left` forwards and remove letters until it fits again.
Taking the max of 26 counts at each step is O(26n), which is already fine.

**Hint 4.** For O(n): you only care about windows *longer* than the best so far. Keep `max_freq`,
the highest count any letter has reached, and never lower it. When the window doesn't fit, slide
it (move `left` by one) instead of shrinking it. A longer window needs a letter count above
`max_freq`, and when that happens `max_freq` is exact again.
