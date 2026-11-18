**Hint 1.** Sorting the values puts every run side by side; one scan then finds the longest
(skip equal neighbours rather than restarting the run). That's O(n log n) and a fine first
answer. For O(n), you can't sort.

**Hint 2.** Put every value in a set. Now "is `x + 1` present?" is an O(1) question, so from any
`x` you can count upwards: `x + 1`, `x + 2`, ...

**Hint 3.** Counting upwards from *every* value is O(n²): in `1, 2, ..., n` you'd walk the same run
n times. Only count from the value where a run begins. How can you tell that `x` begins a run?

**Hint 4.** `x` begins a run exactly when `x - 1` is not in the set. Loop over the set (not over
`nums`, which may repeat a starting value many times) and walk upwards only from those values.
