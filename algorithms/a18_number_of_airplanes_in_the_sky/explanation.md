## Understand the problem

Each flight covers the times `takeoff <= t < landing`: a half-open interval, flying at takeoff
but not at landing. The number of planes in the sky at time `t` is the number of flights covering
`t`, and we want the largest such number over all times.

Picture each flight as a bar on a timeline and stack bars that overlap. The answer is the height
of the tallest stack:

```intervals
flights: [1,10] [2,3] [5,8] [4,7]
peak: [5,7]
caption: three bars are stacked between 5 and 7, so the answer is 3
```

| `airplanes` | Answer | Why |
|---|---|---|
| `[]` | 0 | no planes |
| `[[3, 7]]` | 1 | one plane |
| `[[1, 2], [2, 3], [3, 4]]` | 1 | each lands as the next takes off |
| `[[1, 5], [1, 5], [1, 5]]` | 3 | identical flights all count |
| `[[1, 10], [2, 5], [3, 4]]` | 3 | nested flights: all three fly between 3 and 4 |
| `[[1, 10], [2, 3], [5, 6]]` | 2 | the count goes 1, 2, 1, 2, 1, 0 |

The rule for equal times is part of the problem, so say it before coding: a plane landing at `t`
and one taking off at `t` are not in the sky together.

## Brute force

The count only goes *up* at a takeoff, so the maximum is reached at some takeoff time. For each
takeoff time `t`, count the flights with `takeoff <= t < landing`:

```python
best = 0
for t, _ in airplanes:
    best = max(best, sum(1 for s, e in airplanes if s <= t < e))
```

That is **O(n²)**: 100 million checks for 10,000 planes, far too slow in Python. Counting at every
unit of time doesn't help either: times go up to 10^9, so an array indexed by time is out of the
question.

## The key insight: only takeoffs and landings matter

Which plane is which doesn't matter. All that matters is *when the count changes*: it goes up by
one at each takeoff and down by one at each landing. So squash the bars flat onto the timeline as
**events**: `(takeoff, +1)` and `(landing, -1)`. Sort the events by time and walk them with a
running count. Between two consecutive event times nothing changes, so the largest value the
count reaches is the answer.

This is a **sweep line**: imagine a vertical line moving left to right across the timeline,
stopping only at events.

```array
label: events
values: 1:+1 2:+1 3:-1 4:+1 5:+1 7:-1 8:-1 10:-1
caption: Example 1 as time:change events, sorted by time
---
label: in the sky
values: 1 2 1 2 3 2 1 0
highlight: 4
caption: the running count after each event; it peaks at 3 when the plane at 5 takes off
```

### Ties: land before you take off

When a landing and a takeoff happen at the same time, the order you process them changes the
count you see in between. Take three planes landing at time 5 while three others take off at 5
(`[[1, 5], [2, 5], [3, 5], [5, 8], [5, 9], [5, 10]]`). Three planes are flying just before 5,
and three just after:

```array
label: takeoffs first
values: 4 5 6 5 4 3
highlight: 2
caption: the count after each of the six events at time 5: it briefly reads 6, which never happened
---
label: landings first
values: 2 1 0 1 2 3
caption: the count never goes above the true 3
```

Processing landings first means every count recorded is a real count at some moment. Tuples
make this free: `(5, -1)` sorts before `(5, 1)`, because Python compares tuples element by
element and -1 < 1.

## The solution

```python
class Solution:
    def countOfAirplanes(self, airplanes: list[list[int]]) -> int:
        events = []
        for takeoff, landing in airplanes:
            events.append((takeoff, 1))
            events.append((landing, -1))
        events.sort()  # by time; at equal times (t, -1) comes before (t, 1)

        in_sky = most = 0
        for _, change in events:
            in_sky += change
            most = max(most, in_sky)
        return most
```

**Why it's correct.** After the events at time `t` are processed, `in_sky` equals the number of
flights with `takeoff <= t < landing`: every flight that took off at or before `t` added one, and
every one that landed at or before `t` took it away. That's exactly the count for the whole
stretch until the next event. Within one time, landings come first, so the count dips and then
rises to that true value, and never passes it. So `most` is the largest real count.

## Another way: a min-heap of landing times

Sort the flights by takeoff, and keep a [min-heap](#/algo/learn/data-structures/heaps) of the
landing times of the planes currently in the sky. Before each takeoff, pop every plane that has
landed by then (`landing <= takeoff`, which also handles the tie rule), then push the new plane's
landing time. The heap's size is the number of planes in the sky.

```array
label: heap
values: 10
caption: [1,10] takes off: the heap holds its landing time, size 1
---
label: heap
values: 3 10
caption: [2,3] takes off at 2; nothing has landed yet (the smallest landing is 10): size 2
---
label: heap
values: 7 10
caption: [4,7] takes off at 4; the plane landing at 3 is popped first: size 2
---
label: heap
values: 7 10 8
highlight: 0 1 2
caption: [5,8] takes off at 5; nothing has landed (7 > 5): size 3, the answer
```

```python
import heapq

landings: list[int] = []
most = 0
for takeoff, landing in sorted(airplanes):
    while landings and landings[0] <= takeoff:
        heapq.heappop(landings)  # landed by the time this plane takes off
    heapq.heappush(landings, landing)
    most = max(most, len(landings))
```

This is the same algorithm as "how many meeting rooms do these meetings need?", and it is
handy when you need to know *which* planes are in the air, since the heap holds them.

## Complexity

- **Time: O(n log n).** Sorting 2n events dominates; the sweep is O(n). The heap version is
  also O(n log n): each landing time is pushed and popped at most once.
- **Space: O(n)** for the events (or the heap).

## Pitfalls and variations

- **Takeoffs before landings at equal times.** The most common bug: Example 2 returns 2. If you
  sort events some other way, add the tie-break explicitly. The heap version needs `<=` for the
  same reason.
- **A map of net changes** (`change[t] += 1` at takeoff, `change[t] -= 1` at landing, then walk
  the times in sorted order) also handles ties, because a landing and a takeoff at the same time
  cancel out before the count is read.
- **Small integer times** allow a difference array instead of sorting: O(n + T) for times up to
  `T`. With times up to 10^9, sort.
- **Zero-length flights** (`takeoff == landing`): with landings first they never count. The
  constraints rule them out here, but ask.
- **Weighted events:** Car Pooling (each trip carries several passengers; check the count never
  exceeds the capacity) is the same sweep with `+passengers` and `-passengers`.
- **When is the sky busiest?** Record the event time whenever `most` improves.
- **Flights arrive one at a time** and you must report the maximum after each: keep the net
  changes in a sorted map and re-sweep it (O(n) per flight), or, for O(log n) per flight, use a
  segment tree over the times that supports "add 1 to a range" and "maximum".
- Related: [Merge Intervals](#/algo/problem/a16_merge_intervals) and
  [Non-overlapping Intervals](#/algo/problem/a17_non_overlapping_intervals) use the same sort
  first. See the [intervals pattern](#/algo/learn/patterns/intervals).
