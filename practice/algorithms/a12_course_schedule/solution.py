# The three states a course goes through during the depth-first search.
UNVISITED = 0  # not reached yet
VISITING = 1  # on the current search path: its search has started but not finished
DONE = 2  # fully explored, and no cycle is reachable from it


class Solution:
    def canFinish(self, numCourses: int, prerequisites: list[list[int]]) -> bool:
        # The courses form a directed graph with an arrow b -> a for each pair [a, b]: "take b
        # before a". Every course can be finished exactly when this graph has no cycle.
        # One list per course (not a dict of the courses that appear in a pair), so courses
        # without prerequisites are covered too.
        unlocks: list[list[int]] = [[] for _ in range(numCourses)]
        for course, prereq in prerequisites:
            unlocks[prereq].append(course)

        state = [UNVISITED] * numCourses

        def has_cycle(course: int) -> bool:
            """Explore everything reachable from course; True if that includes a cycle."""
            state[course] = VISITING
            for nxt in unlocks[course]:
                if state[nxt] == VISITING:
                    # An arrow back onto the current path closes a loop.
                    return True
                if state[nxt] == UNVISITED and has_cycle(nxt):
                    return True
                # DONE: explored before and cycle-free. Reaching it again by another route is
                # not a cycle, and it needs no second look (this memo keeps the search linear).
            state[course] = DONE
            return False

        # The graph may be in several disconnected pieces: start a search from every course
        # that no earlier search has reached.
        for course in range(numCourses):
            if state[course] == UNVISITED and has_cycle(course):
                return False
        return True
