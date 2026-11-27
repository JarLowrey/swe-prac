**Hint 1.** The count of planes in the sky only goes up at a takeoff, so the maximum is reached
right after some takeoff. Checking every takeoff time against every plane works, but it is
O(n²).

**Hint 2.** You don't need to know which plane is which, only *when* the count changes. Turn
each flight into two events: +1 at its takeoff time, -1 at its landing time.

**Hint 3.** Sort the events by time and sweep through them with a running count, remembering the
largest value it reaches.

**Hint 4.** Ties decide the answer: at the same time, a landing must come before a takeoff. Store
events as `(time, change)` tuples: `(t, -1)` sorts before `(t, 1)`, so a plain sort gets it
right.
