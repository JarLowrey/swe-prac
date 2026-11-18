**Hint 1.** Draw it: one node per course and an arrow `b → a` for each pair `[a, b]` ("take `b`
before `a`"). In Example 2 the arrows go round in a circle. When exactly is it impossible to
finish?

**Hint 2.** It is impossible exactly when the graph has a cycle. So the task is cycle detection in
a directed graph, which may be in several disconnected pieces: check them all, not just the part
reachable from course 0.

**Hint 3.** One "seen" set is not enough: in Example 3 a search from 0 reaches course 3 twice, by
two routes, and that is not a cycle. Give each course three states: unvisited, *visiting* (on the
path you are exploring right now) and *done* (fully explored). Reaching a visiting course means a
cycle; reaching a done course is fine and needs no second look.

**Hint 4.** Another way: count each course's missing prerequisites. Repeatedly take a course whose
count is 0 and lower the counts of the courses it unlocks. You can finish everything exactly when
this takes all `numCourses` courses (Kahn's algorithm).
