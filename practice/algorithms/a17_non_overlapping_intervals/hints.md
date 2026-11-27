**Hint 1.** Flip the question: removing as few intervals as possible is the same as keeping as
many as possible that don't overlap. The answer is `len(intervals) - kept`.

**Hint 2.** Sort by start. When an interval overlaps the last one you kept, one of the two has to
go. Which one should stay to give the intervals still to come the most room?

**Hint 3.** Keep the one that ends first. Every interval still to come starts at or after both of
them, so the only thing that matters for the future is where the kept one ends, and an earlier
end can only help.

**Hint 4.** Walk the sorted intervals with `prev_end`, the end of the last kept interval. If
`start < prev_end` they overlap (touching is fine): count a removal and set
`prev_end = min(prev_end, end)`. Otherwise keep it: `prev_end = end`.
