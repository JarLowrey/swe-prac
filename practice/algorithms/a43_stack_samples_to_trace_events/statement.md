A sampling profiler records the call stack of a running program at regular moments. Convert its
samples into trace events that say when each function call started and ended.

`samples` is in time order. Each sample is a pair `[timestamp, stack]`, where `stack` lists the
names of the active functions from the outermost call (first) to the innermost (last).
Timestamps strictly increase.

Compare each sample with the previous one. Before the first sample, the previous stack is empty.

- Find the **longest common prefix** of the two stacks: the calls that are still running.
- Each frame of the previous stack after the prefix has **ended** at the current timestamp. Emit
  `["end", timestamp, name]` for each of them, **innermost first**.
- Each frame of the current stack after the prefix has **started** at the current timestamp.
  Emit `["start", timestamp, name]` for each of them, **outermost first**.

A sample's end events come before its start events, and identical consecutive stacks produce no
events. The same name can appear at several depths (recursion): each occurrence is a separate
call. Calls still running at the last sample get no end event.

Return all the events in order. Each event may be a list or a tuple.

**Example 1**

```
Input:  samples = [[1, ["A"]], [2, ["A", "B"]], [3, ["A", "C"]], [4, ["A"]]]
Output: [["start", 1, "A"], ["start", 2, "B"], ["end", 3, "B"], ["start", 3, "C"],
         ["end", 4, "C"]]
```

`A` runs throughout. `B` is called at 2, and by 3 it has returned and `C` has been called. `A`
is still running at the last sample, so it has no end event.

```grid
collabels: t=1 t=2 t=3 t=4
rowlabels: "depth 1" "depth 0"
_ B C _
A A A A
highlight: 1,0 0,1 0,2
caption: one column per sample, outermost call at the bottom; starts highlighted
```

**Example 2**

```
Input:  samples = [[1, ["main", "foo"]], [2, ["main", "foo"]], [3, ["main"]]]
Output: [["start", 1, "main"], ["start", 1, "foo"], ["end", 3, "foo"]]
```

Two calls start at 1, outermost first. The second sample is identical, so it adds nothing.

**Example 3**

```
Input:  samples = [[1, ["main", "f", "g"]], [2, ["main", "h", "g"]]]
Output: [["start", 1, "main"], ["start", 1, "f"], ["start", 1, "g"], ["end", 2, "g"],
         ["end", 2, "f"], ["start", 2, "h"], ["start", 2, "g"]]
```

The common prefix is just `["main"]`. `g` is at the same depth in both samples, but its caller
changed from `f` to `h`, so it is a new call: the old `g` ends (before `f`) and a new one starts
(after `h`).

**Constraints**

- `0 <= len(samples) <= 10^4`, and a stack has at most `10^4` frames (it may be empty).
- `0 <= timestamp <= 10^9`, strictly increasing.
- Function names are 1 to 20 letters, digits or underscores.
