You are given `streams`, a list of `x` data streams, each sorted in ascending order, and an integer
`k`. Return, in ascending order, every value that appears in at least `k` different streams. A
value repeated inside one stream counts only once for that stream.

Think of the streams as live feeds you read from the front, one value at a time, too long to keep
in memory: a sensor log, or a sorted file per server. Here each stream is given as a list, but aim
for a solution that reads each stream once from front to back and keeps only O(x) values in
memory, however long the streams are.

**Example 1**

```
Input:  streams = [[1, 2, 3, 20], [-5, -2, 0, 3], [20, 40, 50, 80]], k = 2
Output: [3, 20]
```

3 is in streams 0 and 1, and 20 is in streams 0 and 2. Every other value is in only one stream.

```array
label: stream 0
values: 1 2 3 20
highlight: 2 3
---
label: stream 1
values: -5 -2 0 3
highlight: 3
---
label: stream 2
values: 20 40 50 80
highlight: 0
caption: the values found in at least 2 streams
```

**Example 2**

```
Input:  streams = [[1, 2, 3], [4, 4, 4], [5, 6]], k = 2
Output: []
```

4 appears three times, but all in stream 1, so it is in only one stream.

**Example 3**

```
Input:  streams = [[5, 6], [4, 5, 20], [20]], k = 2
Output: [5, 20]
```

**Constraints**

- `0 <= x = len(streams) <= 1000`
- `0 <= len(streams[i]) <= 1000`, and each stream is sorted in ascending order (it may repeat a
  value).
- `-10^9 <= streams[i][j] <= 10^9`
- `1 <= k`. `k` may be larger than `x`, and then the answer is `[]`.
