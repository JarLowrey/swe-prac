"""Export the history the app used to keep in data/prac.db, for the in-browser app to import.

    python tools/export_history.py                  # data/prac.db -> swe-prac-history-<date>.json
    python tools/export_history.py --db old.db --out history.json

The app used to run on a local server that stored sessions in SQLite. It now runs in the
browser and keeps them there, so this writes them in the format of the History page's Export
button; Import history on that page adds them to the browser's history. Importing the same file
twice adds nothing the second time.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "prac.db"
FORMAT = "swe-prac-history"  # backend.js BACKUP_FORMAT
VERSION = 1

# The columns every track's sessions share: the timer and its state.
TIMER = (
    "id", "mode", "status", "started_at", "time_limit", "paused_at", "total_paused",
    "finished_at", "final_elapsed",
)  # fmt: skip


def _rows(conn: sqlite3.Connection, table: str, where: str = "", args=()) -> list[dict]:
    """The table's rows as dicts, oldest first; none if this database predates the table."""
    found = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,))
    if found.fetchone() is None:
        return []
    order = "id" if "id" in _columns(conn, table) else "rowid"
    query = f"SELECT * FROM {table} {where} ORDER BY {order}"  # noqa: S608 - fixed names
    return [dict(r) for r in conn.execute(query, args)]


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def _pauses(conn: sqlite3.Connection, table: str, session_id: int) -> list[dict]:
    return [
        {k: p[k] for k in ("started_at", "ended_at", "start_elapsed")}
        for p in _rows(conn, table, "WHERE session_id = ?", (session_id,))
    ]


def _json(text: str | None, default):
    return json.loads(text) if text else default


def coding_sessions(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for row in _rows(conn, "sessions"):
        sid = row["id"]
        completions = {
            str(c["level"]): c["elapsed"]
            for c in _rows(conn, "level_completions", "WHERE session_id = ?", (sid,))
        }
        submissions = [
            {
                "kind": s["kind"],
                "level": s["level"],
                "elapsed": s["elapsed"],
                "at": s["at"],
                "all_passed": bool(s["all_passed"]),
                "breakdown": _json(s["breakdown"], {}),
                "lint_count": s.get("lint_count", 0),
            }
            for s in _rows(conn, "submissions", "WHERE session_id = ?", (sid,))
        ]
        out.append(
            {
                **{k: row[k] for k in TIMER},
                "problem_id": row["problem_id"],
                "current_level": row["current_level"],
                "code": row["code"],
                "scratch": row["scratch"],
                "completions": completions,
                "pauses": _pauses(conn, "pauses", sid),
                "submissions": submissions,
            }
        )
    return out


def algo_sessions(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for row in _rows(conn, "algo_sessions"):
        sid = row["id"]
        submissions = [
            {
                "kind": s["kind"],
                "elapsed": s["elapsed"],
                "at": s["at"],
                "all_passed": bool(s["all_passed"]),
                **{
                    k: s.get(k, 0)
                    for k in ("shown_passed", "shown_total", "hidden_passed", "hidden_total")
                },
                "too_slow": s.get("too_slow", 0),
                "lint_count": s.get("lint_count", 0),
            }
            for s in _rows(conn, "algo_submissions", "WHERE session_id = ?", (sid,))
        ]
        out.append(
            {
                **{k: row[k] for k in TIMER},
                "problem_id": row["problem_id"],
                "code": row["code"],
                "scratch": row["scratch"],
                "solved_at": row["solved_at"],
                "pauses": _pauses(conn, "algo_pauses", sid),
                "submissions": submissions,
            }
        )
    return out


def design_sessions(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for row in _rows(conn, "design_sessions"):
        sid = row["id"]
        starts = {
            str(s["step"]): s["elapsed"]
            for s in _rows(conn, "design_steps", "WHERE session_id = ?", (sid,))
        }
        out.append(
            {
                **{k: row[k] for k in TIMER},
                "question_id": row["question_id"],
                "current_step": row["current_step"],
                "step_starts": starts or {"1": 0},  # step 1 starts with the clock
                "notes": _json(row["notes"], {}),
                "diagram": _json(row["diagram"], {}),
                "assessment": _json(row["assessment"], None),
                "pauses": _pauses(conn, "design_pauses", sid),
            }
        )
    return out


def export(db: Path) -> dict:
    """Everything in the database, as the History page's Export writes it."""
    conn = sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return {
            "format": FORMAT,
            "version": VERSION,
            "exported_at": time.time(),
            "coding": {"sessions": coding_sessions(conn)},
            "algo": {"sessions": algo_sessions(conn)},
            "design": {"sessions": design_sessions(conn)},
        }
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="default: data/prac.db")
    parser.add_argument("--out", type=Path, help="default: swe-prac-history-<date>.json")
    args = parser.parse_args()
    if not args.db.exists():
        print(f"No database at {args.db}.", file=sys.stderr)
        return 1
    data = export(args.db)
    out = args.out or Path(f"swe-prac-history-{datetime.date.today().isoformat()}.json")
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    counts = ", ".join(f"{len(data[t]['sessions'])} {t}" for t in ("coding", "algo", "design"))
    print(f"Wrote {out}: {counts} sessions.")
    print("To load them: open the site's History page and use Import history.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
