"""SQLite persistence for sessions, level completions, pauses and submissions."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('strict', 'pausable')),
    status TEXT NOT NULL CHECK (status IN ('active', 'finished')),
    started_at REAL NOT NULL,
    time_limit INTEGER NOT NULL,
    paused_at REAL,
    total_paused REAL NOT NULL DEFAULT 0,
    current_level INTEGER NOT NULL DEFAULT 1,
    code TEXT NOT NULL,
    scratch TEXT NOT NULL DEFAULT '',
    finished_at REAL,
    final_elapsed REAL
);
CREATE TABLE IF NOT EXISTS level_completions (
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    level INTEGER NOT NULL,
    elapsed REAL NOT NULL,
    at REAL NOT NULL,
    PRIMARY KEY (session_id, level)
);
CREATE TABLE IF NOT EXISTS pauses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    started_at REAL NOT NULL,
    ended_at REAL,
    start_elapsed REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    kind TEXT NOT NULL CHECK (kind IN ('run', 'submit')),
    level INTEGER NOT NULL,
    elapsed REAL NOT NULL,
    at REAL NOT NULL,
    all_passed INTEGER NOT NULL,
    breakdown TEXT NOT NULL,
    lint_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_submissions_session ON submissions(session_id);
"""


def db_path() -> Path:
    return config.DATA_DIR / "prac.db"


def init() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def connect():
    conn = sqlite3.connect(db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
