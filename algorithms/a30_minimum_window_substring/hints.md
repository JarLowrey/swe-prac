**Hint 1.** Brute force: for each start, extend the end one character at a time, counting, until
the substring contains `t`. That's O(n²). What do you learn about the *next* start from the
window you just found?

**Hint 2.** Two facts: a window that contains `t` still contains it when it grows; and if
`s[left..right]` is the shortest window ending at `right`, the shortest window ending at a later
position never starts before `left`. So both ends only ever move forwards: a sliding window.

**Hint 3.** Move `right` to grow the window until it contains `t`. Then move `left` to shrink it
for as long as it still contains `t`, recording each window. When it stops containing `t`, grow
again.

**Hint 4.** Don't compare whole count tables at every step. Keep `need[c]`, how many more `c`s
the window still needs (negative means spare copies), and `missing`, the total still needed.
Adding `c` lowers `missing` only if `need[c] > 0`; removing `c` raises it only if `need[c]`
becomes positive. The window contains `t` exactly when `missing == 0`.
