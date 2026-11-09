"""Mutant: calc_salary treats end_ts as inclusive, so it pays one extra unit when a session crosses the window's end."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Session:
    """A completed session, frozen with the position and pay in effect when it started."""

    start: int
    end: int
    position: str
    compensation: int


@dataclass(frozen=True)
class Promotion:
    position: str
    compensation: int
    start_timestamp: int


@dataclass
class Worker:
    position: str
    compensation: int
    open_since: int | None = None
    pending: Promotion | None = None
    sessions: list[Session] = field(default_factory=list)

    def time_in(self, position: str) -> int:
        return sum(s.end - s.start for s in self.sessions if s.position == position)


def overlap(start: int, end: int, lo: int, hi: int) -> int:
    """Length of the intersection of the half-open ranges [start, end) and [lo, hi)."""
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
        if worker.open_since is None:  # entering: a due promotion applies first
            promotion = worker.pending
            if promotion is not None and timestamp >= promotion.start_timestamp:
                worker.position = promotion.position
                worker.compensation = promotion.compensation
                worker.pending = None
            worker.open_since = timestamp
        else:  # leaving: freeze what was true when the session started
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
        return sum(s.end - s.start for s in worker.sessions)

    # -- Level 2 ------------------------------------------------------------------------
    def top_n_workers(self, timestamp: int, n: int, position: str) -> str:
        """List the top n workers in position by time held in it, as "w1(20), w2(10)"."""
        ranked = [
            (worker_id, worker.time_in(position))
            for worker_id, worker in self.workers.items()
            if worker.position == position
        ]
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
        if worker is None or worker.pending is not None:
            return "invalid_request"
        worker.pending = Promotion(new_position, new_compensation, start_timestamp)
        return "success"

    def calc_salary(self, timestamp: int, worker_id: str, start_ts: int, end_ts: int) -> int | None:
        """Return pay for completed sessions inside [start_ts, end_ts), or None if missing."""
        worker = self.workers.get(worker_id)
        if worker is None:
            return None
        total = 0
        for s in worker.sessions:
            lo, hi = max(s.start, start_ts), min(s.end, end_ts + 1)
            if lo >= hi:
                continue
            doubled = sum(overlap(lo, hi, d_start, d_end) for d_start, d_end in self.double_periods)
            total += (hi - lo + doubled) * s.compensation
        return total

    # -- Level 4 ------------------------------------------------------------------------
    def set_double_time(self, timestamp: int, start_ts: int, end_ts: int) -> None:
        """Make every unit of time inside [start_ts, end_ts) pay double, for all workers."""
        merged: list[tuple[int, int]] = []
        for start, end in sorted([*self.double_periods, (start_ts, end_ts)]):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        self.double_periods = merged
