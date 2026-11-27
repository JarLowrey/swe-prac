class Solution:
    def countOfAirplanes(self, airplanes: list[list[int]]) -> int:
        # Only takeoffs and landings change the number of planes in the sky, so turn every
        # flight into two events: +1 when it takes off, -1 when it lands.
        events: list[tuple[int, int]] = []
        for takeoff, landing in airplanes:
            events.append((takeoff, 1))
            events.append((landing, -1))

        # Sweep the events in time order. Tuples compare element by element, so at equal times
        # (t, -1) sorts before (t, 1): a plane landing at t leaves the sky before one taking off
        # at t is counted, and the count never reads higher than it really was.
        events.sort()

        in_sky = most = 0
        for _, change in events:
            in_sky += change
            most = max(most, in_sky)
        return most
