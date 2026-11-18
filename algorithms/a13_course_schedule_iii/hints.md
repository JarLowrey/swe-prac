**Hint 1.** Suppose you already knew which courses to take. In what order should you take them?
Look at two courses taken back to back where the second one has the earlier last day, and swap
them.

**Hint 2.** Earliest deadline first: a set of courses can be taken if and only if it works when
taken in order of `lastDay`. So sort by `lastDay` (not by duration) and decide course by course.

**Hint 3.** Taking a course whenever it still fits isn't enough: one long course taken early can
block two short ones. Instead, take every course, and when that makes you late, drop the
*longest* course taken so far (possibly the new one). The count stays the same, nothing becomes
late, and you finish as early as possible.

**Hint 4.** Keep the running total of days and a max-heap of the durations taken. In Python,
push `-duration` onto `heapq`. The answer is the heap's size at the end.
