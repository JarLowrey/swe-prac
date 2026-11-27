**Hint 1.** If the streams were small lists, you could turn each into a set and count, for every
value, how many sets contain it. That gives the right answer, but it stores every distinct value.
What breaks when the streams never end?

**Hint 2.** Each stream is sorted, so its front value is its smallest. The smallest front value
across all the streams is the smallest value you haven't processed yet, and no stream can
produce it later. So you can finish values one at a time, in increasing order, like merging
sorted lists.

**Hint 3.** Keep a min-heap of `(front value, stream index)`, one entry per stream. Pop every entry
equal to the smallest value: the number of entries popped is the number of streams that contain
it.

**Hint 4.** Before pushing a stream's next value, skip its other copies of the value you just
counted. Then a stream is counted once, and the heap never holds more than `x` entries.
