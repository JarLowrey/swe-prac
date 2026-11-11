"""Practice sessions: server-side timer, pausing, level completion and results."""

from __future__ import annotations

import json
import sqlite3
import time

from . import config


def clock() -> float:
    """Wall clock; tests monkeypatch this."""
    return time.time()


class SessionError(Exception):
    def __init__(self, message: str, status: int = 409):
        super().__init__(message)
        self.status = status


# -- timer -------------------------------------------------------------------------------
def elapsed(row: sqlite3.Row, now: float | None = None) -> float:
    """Active (unpaused) seconds since the session started."""
    if row["status"] == "finished":
        return row["final_elapsed"]
    now = clock() if now is None else now
    end = row["paused_at"] if row["paused_at"] is not None else now
    return max(0.0, end - row["started_at"] - row["total_paused"])


def timer_state(row: sqlite3.Row) -> dict:
    spent = elapsed(row)
    return {
        "elapsed": spent,
        "limit": row["time_limit"],
        "remaining": max(0.0, row["time_limit"] - spent),
        "overtime": spent >= row["time_limit"],
        "paused": row["paused_at"] is not None,
        "status": row["status"],
        "mode": row["mode"],
    }


# -- queries -----------------------------------------------------------------------------
def get(conn: sqlite3.Connection, session_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        raise SessionError("Session not found.", 404)
    return row


def active(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM sessions WHERE status = 'active' ORDER BY id DESC LIMIT 1"
    ).fetchone()


def completions(conn: sqlite3.Connection, session_id: int) -> dict[int, float]:
    rows = conn.execute(
        "SELECT level, elapsed FROM level_completions WHERE session_id = ? ORDER BY level",
        (session_id,),
    )
    return {r["level"]: r["elapsed"] for r in rows}


def pauses(conn: sqlite3.Connection, session_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM pauses WHERE session_id = ? ORDER BY id", (session_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def submissions(conn: sqlite3.Connection, session_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM submissions WHERE session_id = ? ORDER BY id", (session_id,)
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["breakdown"] = json.loads(d["breakdown"])
        d["all_passed"] = bool(d["all_passed"])
        out.append(d)
    return out


# -- mutations ---------------------------------------------------------------------------
DEFAULT_SCRATCH = (
    "# Scratch: run quick experiments against your class.\nfrom solution import *  # noqa: F403\n\n"
)


def create(
    conn: sqlite3.Connection,
    problem_id: str,
    mode: str,
    starter: str,
    scratch: str = DEFAULT_SCRATCH,
) -> int:
    if mode not in ("strict", "pausable"):
        raise SessionError("Mode must be 'strict' or 'pausable'.", 400)
    if active(conn) is not None:
        raise SessionError("Finish or end your active session before starting another.")
    cur = conn.execute(
        "INSERT INTO sessions (problem_id, mode, status, started_at, time_limit, code, scratch)"
        " VALUES (?, ?, 'active', ?, ?, ?, ?)",
        (problem_id, mode, clock(), config.TIME_LIMIT_SECONDS, starter, scratch),
    )
    return cur.lastrowid


def require_editable(row: sqlite3.Row) -> None:
    if row["status"] != "active":
        raise SessionError("This session has ended.")
    if row["paused_at"] is not None:
        raise SessionError("The session is paused. Resume to continue.")


def save_code(
    conn: sqlite3.Connection, row: sqlite3.Row, code: str | None, scratch: str | None
) -> None:
    require_editable(row)
    if code is not None:
        conn.execute("UPDATE sessions SET code = ? WHERE id = ?", (code, row["id"]))
    if scratch is not None:
        conn.execute("UPDATE sessions SET scratch = ? WHERE id = ?", (scratch, row["id"]))


def pause(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    if row["mode"] != "pausable":
        raise SessionError("This is a strict session: the timer cannot be paused.")
    require_editable(row)
    now = clock()
    if elapsed(row, now) >= row["time_limit"]:
        raise SessionError("Time is up; overtime is untimed, so there is nothing to pause.")
    conn.execute("UPDATE sessions SET paused_at = ? WHERE id = ?", (now, row["id"]))
    conn.execute(
        "INSERT INTO pauses (session_id, started_at, start_elapsed) VALUES (?, ?, ?)",
        (row["id"], now, elapsed(row, now)),
    )


def resume(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    if row["status"] != "active":
        raise SessionError("This session has ended.")
    if row["paused_at"] is None:
        raise SessionError("The session is not paused.")
    now = clock()
    conn.execute(
        "UPDATE sessions SET total_paused = total_paused + ?, paused_at = NULL WHERE id = ?",
        (now - row["paused_at"], row["id"]),
    )
    conn.execute(
        "UPDATE pauses SET ended_at = ? WHERE session_id = ? AND ended_at IS NULL",
        (now, row["id"]),
    )


def record_submission(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    kind: str,
    level: int,
    all_passed: bool,
    breakdown: dict,
    lint_count: int,
) -> None:
    conn.execute(
        "INSERT INTO submissions (session_id, kind, level, elapsed, at, all_passed, breakdown,"
        " lint_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row["id"],
            kind,
            level,
            elapsed(row),
            clock(),
            int(all_passed),
            json.dumps(breakdown),
            lint_count,
        ),
    )


def complete_level(conn: sqlite3.Connection, row: sqlite3.Row) -> int:
    """Mark the current level passed and unlock the next. Returns the new current level."""
    level = row["current_level"]
    if level > len(config.LEVELS):
        return level
    conn.execute(
        "INSERT OR IGNORE INTO level_completions (session_id, level, elapsed, at)"
        " VALUES (?, ?, ?, ?)",
        (row["id"], level, elapsed(row), clock()),
    )
    conn.execute("UPDATE sessions SET current_level = ? WHERE id = ?", (level + 1, row["id"]))
    return level + 1


def finish(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    if row["status"] != "active":
        raise SessionError("This session has already ended.")
    if row["paused_at"] is not None:
        resume(conn, row)
        row = get(conn, row["id"])
    now = clock()
    conn.execute(
        "UPDATE sessions SET status = 'finished', finished_at = ?, final_elapsed = ? WHERE id = ?",
        (now, elapsed(row, now), row["id"]),
    )


# -- results -----------------------------------------------------------------------------
def _level_ratio(subs: list[dict], level: int, before: float | None) -> dict | None:
    """Pass counts for one level's own tests from the last submit (optionally before a time)."""
    for sub in reversed(subs):
        if sub["kind"] != "submit" or sub["level"] != level:
            continue
        if before is not None and sub["elapsed"] > before:
            continue
        counts = sub["breakdown"].get(str(level))
        if counts:
            return {
                "passed": counts["shown_passed"] + counts["hidden_passed"],
                "total": counts["shown_total"] + counts["hidden_total"],
                "shown_passed": counts["shown_passed"],
                "shown_total": counts["shown_total"],
                "hidden_passed": counts["hidden_passed"],
                "hidden_total": counts["hidden_total"],
            }
    return None


def results(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    """Score summary: timed result (at the limit) and final result (including overtime)."""
    limit = row["time_limit"]
    done = completions(conn, row["id"])
    subs = submissions(conn, row["id"])
    pause_rows = pauses(conn, row["id"])
    total_levels = len(config.LEVELS)

    timed_levels = sum(1 for t in done.values() if t <= limit)
    final_levels = len(done)
    levels = []
    previous = 0.0
    for level in config.LEVELS:
        t = done.get(level)
        levels.append(
            {
                "level": level,
                "completed_at": t,
                "split": None if t is None else t - previous,
                "target": config.PACING_SECONDS[level],
                "delta": None if t is None else t - config.PACING_SECONDS[level],
                "overtime": t is not None and t > limit,
            }
        )
        if t is not None:
            previous = t

    timed_stop = timed_levels + 1 if timed_levels < total_levels else None
    final_stop = final_levels + 1 if final_levels < total_levels else None
    spent = elapsed(row)
    paused_total = sum(
        (p["ended_at"] if p["ended_at"] is not None else clock()) - p["started_at"]
        for p in pause_rows
    )
    return {
        "time_limit": limit,
        "elapsed": spent,
        "overtime_seconds": max(0.0, spent - limit),
        "timed": {
            "levels_completed": timed_levels,
            "stopped_level": timed_stop,
            "stopped_level_ratio": _level_ratio(subs, timed_stop, limit) if timed_stop else None,
        },
        "final": {
            "levels_completed": final_levels,
            "stopped_level": final_stop,
            "stopped_level_ratio": _level_ratio(subs, final_stop, None) if final_stop else None,
        },
        "levels": levels,
        "pauses": {"count": len(pause_rows), "total_seconds": paused_total},
        "runs": sum(1 for s in subs if s["kind"] == "run"),
        "submits": sum(1 for s in subs if s["kind"] == "submit"),
    }
