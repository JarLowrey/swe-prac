"""tools/export_history.py: the old server's SQLite history, in the browser's backup format."""

from __future__ import annotations

import contextlib
import io
import json
import sqlite3
import sys
from pathlib import Path

from support import TempDirCase

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import export_history  # noqa: E402

# The tables as the server last created them (swe_prac/db.py before the app moved to the browser).
CODING_AND_DESIGN = """
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, problem_id TEXT NOT NULL, mode TEXT NOT NULL,
    status TEXT NOT NULL, started_at REAL NOT NULL, time_limit INTEGER NOT NULL, paused_at REAL,
    total_paused REAL NOT NULL DEFAULT 0, current_level INTEGER NOT NULL DEFAULT 1,
    code TEXT NOT NULL, scratch TEXT NOT NULL DEFAULT '', finished_at REAL, final_elapsed REAL
);
CREATE TABLE level_completions (
    session_id INTEGER NOT NULL, level INTEGER NOT NULL, elapsed REAL NOT NULL, at REAL NOT NULL,
    PRIMARY KEY (session_id, level)
);
CREATE TABLE pauses (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, started_at REAL NOT NULL,
    ended_at REAL, start_elapsed REAL NOT NULL
);
CREATE TABLE design_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, question_id TEXT NOT NULL, mode TEXT NOT NULL,
    status TEXT NOT NULL, started_at REAL NOT NULL, time_limit INTEGER NOT NULL, paused_at REAL,
    total_paused REAL NOT NULL DEFAULT 0, current_step INTEGER NOT NULL DEFAULT 1,
    notes TEXT NOT NULL DEFAULT '{}', diagram TEXT NOT NULL DEFAULT '{}', assessment TEXT,
    finished_at REAL, final_elapsed REAL
);
CREATE TABLE design_steps (
    session_id INTEGER NOT NULL, step INTEGER NOT NULL, elapsed REAL NOT NULL, at REAL NOT NULL,
    PRIMARY KEY (session_id, step)
);
CREATE TABLE design_pauses (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, started_at REAL NOT NULL,
    ended_at REAL, start_elapsed REAL NOT NULL
);
"""
SUBMISSIONS = """
CREATE TABLE submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, kind TEXT NOT NULL,
    level INTEGER NOT NULL, elapsed REAL NOT NULL, at REAL NOT NULL, all_passed INTEGER NOT NULL,
    breakdown TEXT NOT NULL, lint_count INTEGER NOT NULL DEFAULT 0
);
"""
ALGO = """
CREATE TABLE algo_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, problem_id TEXT NOT NULL, mode TEXT NOT NULL,
    status TEXT NOT NULL, started_at REAL NOT NULL, time_limit INTEGER NOT NULL, paused_at REAL,
    total_paused REAL NOT NULL DEFAULT 0, code TEXT NOT NULL, scratch TEXT NOT NULL DEFAULT '',
    solved_at REAL, finished_at REAL, final_elapsed REAL
);
CREATE TABLE algo_pauses (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, started_at REAL NOT NULL,
    ended_at REAL, start_elapsed REAL NOT NULL
);
CREATE TABLE algo_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, kind TEXT NOT NULL,
    elapsed REAL NOT NULL, at REAL NOT NULL, all_passed INTEGER NOT NULL,
    shown_passed INTEGER NOT NULL, shown_total INTEGER NOT NULL,
    hidden_passed INTEGER NOT NULL DEFAULT 0, hidden_total INTEGER NOT NULL DEFAULT 0,
    too_slow INTEGER NOT NULL DEFAULT 0, lint_count INTEGER NOT NULL DEFAULT 0
);
"""
BREAKDOWN = {"1": {"shown_passed": 3, "shown_total": 3, "hidden_passed": 8, "hidden_total": 8}}


class ExportHistoryTests(TempDirCase):
    def make_db(self, schema: str, rows: str) -> Path:
        path = self.tmp_path / "prac.db"
        conn = sqlite3.connect(path)
        conn.executescript(schema + rows)
        conn.commit()
        conn.close()
        return path

    def test_every_track_exports_in_the_browsers_format(self):
        db = self.make_db(
            CODING_AND_DESIGN + SUBMISSIONS + ALGO,
            f"""
            INSERT INTO sessions VALUES
                (1, 'p1_file_store', 'pausable', 'finished', 1000.0, 5400, NULL, 30.0, 2,
                 'class A: ...', 'print(1)', 2000.0, 970.0);
            INSERT INTO level_completions VALUES (1, 1, 600.0, 1630.0);
            INSERT INTO pauses VALUES (1, 1, 1100.0, 1130.0, 100.0);
            INSERT INTO submissions VALUES
                (1, 1, 'run', 1, 300.0, 1330.0, 0, '{{}}', 2),
                (2, 1, 'submit', 1, 600.0, 1630.0, 1, '{json.dumps(BREAKDOWN)}', 0);
            INSERT INTO algo_sessions VALUES
                (1, 'a01_two_sum', 'strict', 'active', 3000.0, 1200, NULL, 0, 'class S: ...',
                 '', 90.5, NULL, NULL);
            INSERT INTO algo_submissions VALUES
                (1, 1, 'submit', 90.5, 3090.5, 1, 2, 2, 11, 11, 0, 1);
            INSERT INTO design_sessions VALUES
                (1, 'd01_url_shortener', 'strict', 'finished', 5000.0, 2700, NULL, 0, 3,
                 '{{"1": "reqs"}}', '{{"nodes": [], "edges": []}}',
                 '{{"checklist": [0, 2], "key_points": [1]}}', 6000.0, 1000.0);
            INSERT INTO design_steps VALUES (1, 1, 0.0, 5000.0), (1, 3, 400.0, 5400.0);
            """,
        )
        data = export_history.export(db)
        self.assertEqual((data["format"], data["version"]), ("swe-prac-history", 1))
        (coding,) = data["coding"]["sessions"]
        self.assertEqual(
            coding,
            {
                "id": 1,
                "mode": "pausable",
                "status": "finished",
                "started_at": 1000.0,
                "time_limit": 5400,
                "paused_at": None,
                "total_paused": 30.0,
                "finished_at": 2000.0,
                "final_elapsed": 970.0,
                "problem_id": "p1_file_store",
                "current_level": 2,
                "code": "class A: ...",
                "scratch": "print(1)",
                "completions": {"1": 600.0},
                "pauses": [{"started_at": 1100.0, "ended_at": 1130.0, "start_elapsed": 100.0}],
                "submissions": [
                    {
                        "kind": "run",
                        "level": 1,
                        "elapsed": 300.0,
                        "at": 1330.0,
                        "all_passed": False,
                        "breakdown": {},
                        "lint_count": 2,
                    },
                    {
                        "kind": "submit",
                        "level": 1,
                        "elapsed": 600.0,
                        "at": 1630.0,
                        "all_passed": True,
                        "breakdown": BREAKDOWN,
                        "lint_count": 0,
                    },
                ],
            },
        )
        (algo,) = data["algo"]["sessions"]
        self.assertEqual(
            (algo["problem_id"], algo["status"], algo["solved_at"]), ("a01_two_sum", "active", 90.5)
        )
        self.assertEqual(
            algo["submissions"],
            [
                {
                    "kind": "submit",
                    "elapsed": 90.5,
                    "at": 3090.5,
                    "all_passed": True,
                    "shown_passed": 2,
                    "shown_total": 2,
                    "hidden_passed": 11,
                    "hidden_total": 11,
                    "too_slow": 0,
                    "lint_count": 1,
                }
            ],
        )
        (design,) = data["design"]["sessions"]
        self.assertEqual(design["step_starts"], {"1": 0.0, "3": 400.0})
        self.assertEqual(design["current_step"], 3)
        self.assertEqual(design["notes"], {"1": "reqs"})
        self.assertEqual(design["diagram"], {"nodes": [], "edges": []})
        self.assertEqual(design["assessment"], {"checklist": [0, 2], "key_points": [1]})
        self.assertEqual(design["pauses"], [])

    def test_a_database_from_before_the_algorithm_track_and_lint_counts(self):
        old_submissions = SUBMISSIONS.replace(", lint_count INTEGER NOT NULL DEFAULT 0", "")
        db = self.make_db(
            CODING_AND_DESIGN + old_submissions,
            """
            INSERT INTO sessions VALUES
                (1, 'p1_file_store', 'strict', 'finished', 1.0, 5400, NULL, 0, 1, '', '', 2.0, 1.0);
            INSERT INTO submissions VALUES (1, 1, 'run', 1, 0.5, 1.5, 0, '{}');
            INSERT INTO design_sessions VALUES
                (1, 'd01_url_shortener', 'strict', 'finished', 1.0, 2700, NULL, 0, 1, '{}', '{}',
                 NULL, 2.0, 1.0);
            """,
        )
        data = export_history.export(db)
        self.assertEqual(data["coding"]["sessions"][0]["submissions"][0]["lint_count"], 0)
        self.assertEqual(data["algo"]["sessions"], [])
        (design,) = data["design"]["sessions"]
        self.assertEqual(design["step_starts"], {"1": 0})
        self.assertIsNone(design["assessment"])

    def test_the_command_writes_the_file_and_leaves_the_database_alone(self):
        db = self.make_db(CODING_AND_DESIGN + SUBMISSIONS + ALGO, "")
        before = db.read_bytes()
        out = self.tmp_path / "history.json"
        self.patch(sys, "argv", ["export_history.py", "--db", str(db), "--out", str(out)])
        printed = io.StringIO()
        self.enterContext(contextlib.redirect_stdout(printed))
        self.enterContext(contextlib.redirect_stderr(printed))
        self.assertEqual(export_history.main(), 0)
        self.assertIn("0 coding, 0 algo, 0 design sessions", printed.getvalue())
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["coding"], {"sessions": []})
        self.assertEqual(db.read_bytes(), before)

        self.patch(sys, "argv", ["export_history.py", "--db", str(self.tmp_path / "missing.db")])
        self.assertEqual(export_history.main(), 1)
        self.assertIn("No database at", printed.getvalue())
