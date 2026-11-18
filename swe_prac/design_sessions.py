"""System design sessions: a 45-minute clock, the seven framework steps, notes and a diagram.

The clock, pausing and finishing are the coding sessions' code (sessions.py) run against the
design tables. There is nothing to auto-grade here: after the session you tick a self-review
checklist on the review page, and that is the score.
"""

from __future__ import annotations

import json
import sqlite3

from . import config, sessions
from .sessions import SessionError, clock, elapsed

TABLES = sessions.Tables("design_sessions", "design_pauses")


# -- queries -----------------------------------------------------------------------------
def get(conn: sqlite3.Connection, session_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM design_sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        raise SessionError("Session not found.", 404)
    return row


def active(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM design_sessions WHERE status = 'active' ORDER BY id DESC LIMIT 1"
    ).fetchone()


def notes(row: sqlite3.Row) -> dict[str, str]:
    return json.loads(row["notes"])


def diagram(row: sqlite3.Row) -> dict:
    return json.loads(row["diagram"])


def step_starts(conn: sqlite3.Connection, session_id: int) -> dict[int, float]:
    rows = conn.execute(
        "SELECT step, elapsed FROM design_steps WHERE session_id = ? ORDER BY step", (session_id,)
    )
    return {r["step"]: r["elapsed"] for r in rows}


def pauses(conn: sqlite3.Connection, session_id: int) -> list[dict]:
    return sessions.pauses(conn, session_id, TABLES)


def assessment(row: sqlite3.Row) -> dict | None:
    return json.loads(row["assessment"]) if row["assessment"] else None


# -- mutations ---------------------------------------------------------------------------
def create(conn: sqlite3.Connection, question_id: str, mode: str, starter: dict[str, str]) -> int:
    if mode not in ("strict", "pausable"):
        raise SessionError("Mode must be 'strict' or 'pausable'.", 400)
    if active(conn) is not None:
        raise SessionError("Finish or end your system design session before starting another.")
    now = clock()
    cur = conn.execute(
        "INSERT INTO design_sessions (question_id, mode, status, started_at, time_limit, notes)"
        " VALUES (?, ?, 'active', ?, ?, ?)",
        (question_id, mode, now, config.DESIGN_TIME_LIMIT_SECONDS, json.dumps(starter)),
    )
    # Step 1 (requirements) starts with the clock.
    conn.execute(
        "INSERT INTO design_steps (session_id, step, elapsed, at) VALUES (?, 1, 0, ?)",
        (cur.lastrowid, now),
    )
    return cur.lastrowid


def save(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    new_notes: dict[str, str] | None,
    new_diagram: dict | None,
    step_count: int,
) -> None:
    """Merge notes for known steps and replace the diagram. Refused while paused or finished."""
    sessions.require_editable(row)
    if new_notes is not None:
        known = {str(n) for n in range(1, step_count + 1)}
        merged = notes(row)
        merged.update({k: v for k, v in new_notes.items() if k in known})
        conn.execute(
            "UPDATE design_sessions SET notes = ? WHERE id = ?", (json.dumps(merged), row["id"])
        )
    if new_diagram is not None:
        conn.execute(
            "UPDATE design_sessions SET diagram = ? WHERE id = ?",
            (json.dumps(new_diagram), row["id"]),
        )


def start_step(conn: sqlite3.Connection, row: sqlite3.Row, step: int, step_count: int) -> None:
    """Move on to a later step. Steps only go forward; skipping one is allowed."""
    sessions.require_editable(row)
    if not row["current_step"] < step <= step_count:
        raise SessionError(f"You're on step {row['current_step']}; you can only move forward.", 400)
    conn.execute(
        "INSERT INTO design_steps (session_id, step, elapsed, at) VALUES (?, ?, ?, ?)",
        (row["id"], step, elapsed(row), clock()),
    )
    conn.execute("UPDATE design_sessions SET current_step = ? WHERE id = ?", (step, row["id"]))


def pause(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    sessions.pause(conn, row, TABLES)


def resume(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    sessions.resume(conn, row, TABLES)


def finish(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    sessions.finish(conn, row, TABLES)


def save_assessment(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    checklist: list[int],
    key_points: list[int],
    sizes: tuple[int, int],
) -> dict:
    """Store which checklist items and key points you ticked (indices). Only after the session."""
    if row["status"] != "finished":
        raise SessionError("Self-review opens when the session ends.")
    picked = {"checklist": checklist, "key_points": key_points}
    for (name, items), size in zip(picked.items(), sizes, strict=True):
        if any(not 0 <= i < size for i in items):
            raise SessionError(f"{name}: item index out of range.", 400)
        picked[name] = sorted(set(items))
    conn.execute(
        "UPDATE design_sessions SET assessment = ? WHERE id = ?", (json.dumps(picked), row["id"])
    )
    return picked


# -- results -----------------------------------------------------------------------------
def score(row: sqlite3.Row, sizes: tuple[int, int]) -> dict | None:
    """Self-review score, or None if you haven't reviewed this session yet."""
    picked = assessment(row)
    if picked is None:
        return None
    checklist = sum(1 for i in picked["checklist"] if i < sizes[0])
    key_points = sum(1 for i in picked["key_points"] if i < sizes[1])
    return {
        "done": checklist + key_points,
        "total": sizes[0] + sizes[1],
        "checklist": checklist,
        "key_points": key_points,
    }


def results(conn: sqlite3.Connection, row: sqlite3.Row, steps: list[dict]) -> dict:
    """Time spent on each step against its target, and the overall clock."""
    starts = step_starts(conn, row["id"])
    spent_total = elapsed(row)
    limit = row["time_limit"]
    out = []
    target_start = 0.0
    for s in steps:
        n = s["step"]
        start = starts.get(n)
        later = [t for m, t in starts.items() if m > n]
        end = min(later) if later else spent_total
        spent = None if start is None else max(0.0, end - start)
        out.append(
            {
                "step": n,
                "title": s["title"],
                "target": s["minutes"] * 60,
                "target_start": target_start,
                "started_at": start,
                "spent": spent,
                "delta": None if spent is None else spent - s["minutes"] * 60,
                "overtime": start is not None and start > limit,
            }
        )
        target_start += s["minutes"] * 60
    return {
        "time_limit": limit,
        "elapsed": spent_total,
        "overtime_seconds": max(0.0, spent_total - limit),
        "steps": out,
        "steps_reached": len(starts),
        "pauses": sessions.pause_summary(pauses(conn, row["id"])),
    }
