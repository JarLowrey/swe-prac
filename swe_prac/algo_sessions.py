"""Algorithm sessions: one problem against a clock set by its difficulty (20, 30 or 40 minutes).

The clock, pausing and finishing are sessions.py's code run against the algo tables. Run checks
the shown examples; Submit adds the hidden tests, and the first submit that passes all of them
marks the problem solved. The time of that submit is kept, so the review can say whether it was
solved within the limit (overtime continues untimed, as in the coding track).
"""

from __future__ import annotations

import sqlite3

from . import sessions
from .sessions import SessionError, clock, elapsed

TABLES = sessions.Tables("algo_sessions", "algo_pauses")
COUNT_KEYS = ("shown_passed", "shown_total", "hidden_passed", "hidden_total", "too_slow")


# -- queries -----------------------------------------------------------------------------
def get(conn: sqlite3.Connection, session_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM algo_sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        raise SessionError("Session not found.", 404)
    return row


def active(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM algo_sessions WHERE status = 'active' ORDER BY id DESC LIMIT 1"
    ).fetchone()


def pauses(conn: sqlite3.Connection, session_id: int) -> list[dict]:
    return sessions.pauses(conn, session_id, TABLES)


def submissions(conn: sqlite3.Connection, session_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM algo_submissions WHERE session_id = ? ORDER BY id", (session_id,)
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["all_passed"] = bool(d["all_passed"])
        out.append(d)
    return out


# -- mutations ---------------------------------------------------------------------------
def create(
    conn: sqlite3.Connection,
    problem_id: str,
    mode: str,
    time_limit: int,
    starter: str,
    scratch: str,
) -> int:
    if mode not in ("strict", "pausable"):
        raise SessionError("Mode must be 'strict' or 'pausable'.", 400)
    if active(conn) is not None:
        raise SessionError("Finish or end your algorithms session before starting another.")
    cur = conn.execute(
        "INSERT INTO algo_sessions (problem_id, mode, status, started_at, time_limit, code,"
        " scratch) VALUES (?, ?, 'active', ?, ?, ?, ?)",
        (problem_id, mode, clock(), time_limit, starter, scratch),
    )
    return cur.lastrowid


def save_code(
    conn: sqlite3.Connection, row: sqlite3.Row, code: str | None, scratch: str | None
) -> None:
    sessions.require_editable(row)
    if code is not None:
        conn.execute("UPDATE algo_sessions SET code = ? WHERE id = ?", (code, row["id"]))
    if scratch is not None:
        conn.execute("UPDATE algo_sessions SET scratch = ? WHERE id = ?", (scratch, row["id"]))


def pause(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    sessions.pause(conn, row, TABLES)


def resume(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    sessions.resume(conn, row, TABLES)


def finish(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    sessions.finish(conn, row, TABLES)


def record_submission(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    kind: str,
    all_passed: bool,
    counts: dict[str, int],
    lint_count: int,
) -> bool:
    """Store a run or submit. True when this submit solved the problem for the first time."""
    spent = elapsed(row)
    conn.execute(
        "INSERT INTO algo_submissions (session_id, kind, elapsed, at, all_passed, shown_passed,"
        " shown_total, hidden_passed, hidden_total, too_slow, lint_count)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row["id"],
            kind,
            spent,
            clock(),
            int(all_passed),
            *(counts[k] for k in COUNT_KEYS),
            lint_count,
        ),
    )
    if kind == "submit" and all_passed and row["solved_at"] is None:
        conn.execute("UPDATE algo_sessions SET solved_at = ? WHERE id = ?", (spent, row["id"]))
        return True
    return False


# -- results -----------------------------------------------------------------------------
def _passed(sub: dict) -> int:
    return sub["shown_passed"] + sub["hidden_passed"]


def _best(submits: list[dict], before: float | None) -> dict | None:
    """The submit that passed the most tests (the earliest of equals), optionally by a time."""
    pool = [s for s in submits if before is None or s["elapsed"] <= before]
    if not pool:
        return None
    best = max(pool, key=lambda s: (_passed(s), -s["elapsed"]))
    return {
        "passed": _passed(best),
        "total": best["shown_total"] + best["hidden_total"],
        "elapsed": best["elapsed"],
        "too_slow": best["too_slow"],
    }


def results(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    """Timed result (by the limit) and final result (including overtime)."""
    limit = row["time_limit"]
    subs = submissions(conn, row["id"])
    submits = [s for s in subs if s["kind"] == "submit"]
    solved_at = row["solved_at"]
    spent = elapsed(row)
    return {
        "time_limit": limit,
        "elapsed": spent,
        "overtime_seconds": max(0.0, spent - limit),
        "solved_at": solved_at,
        "timed": {
            "solved": solved_at is not None and solved_at <= limit,
            "best": _best(submits, limit),
        },
        "final": {"solved": solved_at is not None, "best": _best(submits, None)},
        "pauses": sessions.pause_summary(pauses(conn, row["id"])),
        "runs": len(subs) - len(submits),
        "submits": len(submits),
    }
