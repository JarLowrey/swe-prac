**Hint 1.** You could append `newInterval`, sort, and run the
[Merge Intervals](#/algo/problem/a16_merge_intervals) pass: O(n log n). But the list is already
sorted and overlap-free. Only one interval is out of place; what does that buy you?

**Hint 2.** Every existing interval falls into one of three groups: entirely before
`newInterval` (it ends before `newInterval` starts), overlapping it, or entirely after it (it
starts after `newInterval` ends). Because the list is sorted, the three groups come in that
order, each as one unbroken run.

**Hint 3.** Walk the list once with an index: copy the "before" run, then absorb each
overlapping interval into the new one (the smaller start, the larger end), append the merged
interval, then copy the rest.

**Hint 4.** Use strict comparisons for the runs you copy: `end_i < start` is before and
`start_i > end` is after. An interval that only touches `newInterval` is in neither, so it gets
merged. Don't forget the cases where nothing overlaps: the merged interval must still be
appended, possibly first or last.
