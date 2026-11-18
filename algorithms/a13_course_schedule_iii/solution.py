import heapq


class Solution:
    def scheduleCourse(self, courses: list[list[int]]) -> int:
        # heapq is a min-heap, so durations are stored negated: taken[0] is minus the longest.
        taken: list[int] = []
        day = 0  # the day on which the courses taken so far finish

        # Earliest deadline first: any set of courses that can be taken on time can be taken in
        # lastDay order, so decide course by course in that order.
        for duration, last_day in sorted(courses, key=lambda c: c[1]):
            heapq.heappush(taken, -duration)
            day += duration
            if day > last_day:  # late (finishing exactly on last_day is fine)
                # Drop the longest course taken so far, which may be this one. The count is the
                # same as before this course, every remaining course finishes no later than
                # before, and the total is as small as it can be for that count. One drop is
                # enough: the longest is at least as long as this course, so we finish no later
                # than the previous finishing day, which met an earlier deadline.
                longest = -heapq.heappop(taken)
                day -= longest
        return len(taken)
