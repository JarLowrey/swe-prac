"""Reference solution for Problem 5: Worker time tracker."""

from __future__ import annotations

from dataclasses import dataclass, field

# Design in brief
# ---------------
# - A completed session is stored as a frozen (start, end, position, compensation) copy, taken
#   from the worker when the session is closed. A promotion only ever applies while the worker
#   is OUT of a session, so those values equal the ones at the session's start. Promotions
#   therefore never need to rewrite history, and salary can read each session's own rate.
# - promote() only records a pending promotion. register() applies it lazily, at the first
#   entry at or after its start_timestamp.
# - Double-time periods are kept merged and non-overlapping, so a session's bonus is a plain
#   sum of overlaps with no unit counted twice.


@dataclass(frozen=True)
class Session:
    """A completed session, frozen with the position and pay in effect when it started."""

    start: int
    end: int
    position: str
    compensation: int


@dataclass(frozen=True)
class Promotion:
    # Frozen: a pending promotion is never edited, only applied (and cleared) or left alone.
    position: str
    compensation: int
    start_timestamp: int


@dataclass
class Worker:
    # The CURRENT position and pay. Past sessions keep their own copies.
    position: str
    compensation: int
    open_since: int | None = None  # entry time of the current session; None while out
    pending: Promotion | None = None  # at most one scheduled promotion at a time
    sessions: list[Session] = field(default_factory=list)  # completed sessions only

    def time_in(self, position: str) -> int:
        # Time spent in `position`, counted from completed sessions only. A worker who has since
        # been promoted away keeps the time they spent in their old position.
        return sum(s.end - s.start for s in self.sessions if s.position == position)


def overlap(start: int, end: int, lo: int, hi: int) -> int:
    """Length of the intersection of the half-open ranges [start, end) and [lo, hi)."""
    # Disjoint ranges make the difference negative, so clamp it to 0.
    return max(0, min(end, hi) - max(start, lo))


class WorkerTracker:
    def __init__(self) -> None:
        self.workers: dict[str, Worker] = {}
        self.double_periods: list[tuple[int, int]] = []  # sorted, merged, non-overlapping

    # -- Level 1 ------------------------------------------------------------------------
    def add_worker(self, timestamp: int, worker_id: str, position: str, compensation: int) -> bool:
        """Add a worker paid compensation per time unit; return False if the worker exists."""
        if worker_id in self.workers:
            return False
        self.workers[worker_id] = Worker(position, compensation)
        return True

    def register(self, timestamp: int, worker_id: str) -> str:
        """Alternate between entering and leaving; return "registered" or "invalid_request"."""
        worker = self.workers.get(worker_id)
        if worker is None:
            return "invalid_request"
        # One method toggles the worker: out -> in on one call, in -> out on the next.
        if worker.open_since is None:  # entering: a due promotion applies first
            promotion = worker.pending
            # `>=`: a promotion that starts exactly at this entry applies to this very session.
            if promotion is not None and timestamp >= promotion.start_timestamp:
                worker.position = promotion.position
                worker.compensation = promotion.compensation
                worker.pending = None
            worker.open_since = timestamp
        else:  # leaving: freeze what was true when the session started
            # The promotion could not have been applied mid-session, so the worker's current
            # position and pay are still the ones from the session's start.
            worker.sessions.append(
                Session(worker.open_since, timestamp, worker.position, worker.compensation)
            )
            worker.open_since = None
        return "registered"

    def get(self, timestamp: int, worker_id: str) -> int | None:
        """Return the total time across completed sessions, or None for a missing worker."""
        worker = self.workers.get(worker_id)
        if worker is None:
            return None
        # Only completed sessions count: an open session adds nothing until the worker leaves.
        return sum(s.end - s.start for s in worker.sessions)

    # -- Level 2 ------------------------------------------------------------------------
    def top_n_workers(self, timestamp: int, n: int, position: str) -> str:
        """List the top n workers in position by time held in it, as "w1(20), w2(10)"."""
        # Only workers whose CURRENT position matches are listed, but each one is ranked by the
        # time of the sessions they spent in that position (see Worker.time_in). Workers with
        # 0 time are included.
        ranked = [
            (worker_id, worker.time_in(position))
            for worker_id, worker in self.workers.items()
            if worker.position == position
        ]
        # Time descending, then id ascending.
        ranked.sort(key=lambda item: (-item[1], item[0]))
        return ", ".join(f"{worker_id}({time})" for worker_id, time in ranked[:n])

    # -- Level 3 ------------------------------------------------------------------------
    def promote(
        self,
        timestamp: int,
        worker_id: str,
        new_position: str,
        new_compensation: int,
        start_timestamp: int,
    ) -> str:
        """Schedule a promotion from the first entry at or after start_timestamp."""
        worker = self.workers.get(worker_id)
        # One pending promotion per worker: a second one is refused until register() applies
        # the first.
        if worker is None or worker.pending is not None:
            return "invalid_request"
        # Only record it. Nothing about the worker changes until their next qualifying entry.
        worker.pending = Promotion(new_position, new_compensation, start_timestamp)
        return "success"

    def calc_salary(self, timestamp: int, worker_id: str, start_ts: int, end_ts: int) -> int | None:
        """Return pay for completed sessions inside [start_ts, end_ts), or None if missing."""
        worker = self.workers.get(worker_id)
        if worker is None:
            return None
        total = 0
        for s in worker.sessions:
            # Clip the session to the window. An empty result means no overlap at all.
            lo, hi = max(s.start, start_ts), min(s.end, end_ts)
            if lo >= hi:
                continue
            # Double time pays each doubled unit twice: one extra copy of it. Measure the
            # overlap against the CLIPPED range, so double time outside the window is not paid.
            # The periods are merged and disjoint, so no unit is counted twice here.
            doubled = sum(overlap(lo, hi, d_start, d_end) for d_start, d_end in self.double_periods)
            # Pay at the session's own frozen rate, not the worker's current one.
            total += (hi - lo + doubled) * s.compensation
        return total

    # -- Level 4 ------------------------------------------------------------------------
    def set_double_time(self, timestamp: int, start_ts: int, end_ts: int) -> None:
        """Make every unit of time inside [start_ts, end_ts) pay double, for all workers."""
        # Why merge: two overlapping double-time periods must not pay quadruple on the shared
        # part. Sort all periods by start, then fold: a period that starts at or before the end
        # of the previous one extends it; otherwise it begins a new one. (`<=` also joins
        # periods that merely touch, which changes no overlap length.)
        merged: list[tuple[int, int]] = []
        for start, end in sorted([*self.double_periods, (start_ts, end_ts)]):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        self.double_periods = merged
