"""HTTP API for algorithm practice, mounted under /api/algo.

Hidden tests, hints, the explanation and the reference solution stay off the session payload:
they appear on the review page, or on the study pages while no session on that problem runs.
Submit reports the hidden tests as counts only.
"""

from __future__ import annotations

import random
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import algo_sessions as al
from . import algorithms, config, db, execution, pages
from .sessions import SessionError, timer_state

router = APIRouter(prefix="/api/algo")

# Copied next to solution.py as helpers.py when scratch runs: builds lists, trees and graphs.
HELPERS_SOURCE = config.PACKAGE_DIR / "scratch_helpers.py"


class StartBody(BaseModel):
    problem_id: str | None = None  # None means random, from the problems matching the filters
    mode: str
    prefer_unseen: bool = True
    difficulty: str | None = None
    pattern: str | None = None


class CodeBody(BaseModel):
    code: str | None = None
    scratch: str | None = None


# -- helpers -----------------------------------------------------------------------------
def _problem(problem_id: str) -> algorithms.Problem:
    try:
        return algorithms.get(problem_id)
    except algorithms.ProblemNotFound:
        raise HTTPException(404, f"Unknown problem {problem_id!r}") from None


def _workdir(session_id: int) -> Path:
    return config.DATA_DIR / "algo_sessions" / str(session_id)


def _question(problem: algorithms.Problem) -> dict:
    """What the solver sees: the statement and the examples (the shown tests)."""
    return {
        "statement_html": algorithms.statement_html(problem),
        "params": algorithms.param_names(problem),
        "examples": algorithms.shown_cases(problem),
    }


def _payload(row) -> dict:
    problem = _problem(row["problem_id"])
    return {
        "id": row["id"],
        "problem": problem.public(),
        "mode": row["mode"],
        "status": row["status"],
        **_question(problem),
        "code": row["code"],
        "scratch": row["scratch"],
        "solved_at": row["solved_at"],
        "timer": timer_state(row),
    }


def _too_slow(result: dict | None) -> bool:
    return bool(result and not result["passed"] and (result["error"] or "").startswith("Too slow"))


def _summarize(tests: list[dict], run: execution.TestRun) -> tuple[list[dict], dict, bool]:
    """Full detail for the shown tests; counts only for the hidden ones."""
    shown = []
    counts = dict.fromkeys(al.COUNT_KEYS, 0)
    all_passed = run.import_error is None and run.crashed is None
    for test in tests:
        result = run.results.get(test["id"])
        passed = bool(result and result["passed"])
        all_passed &= passed
        visibility = test["visibility"]
        counts[f"{visibility}_total"] += 1
        counts[f"{visibility}_passed"] += passed
        counts["too_slow"] += _too_slow(result)
        if visibility == "shown":
            step = result["steps"][0] if result and result["steps"] else {}
            shown.append(
                {
                    "id": test["id"],
                    "name": test["name"],
                    "passed": passed,
                    "ran": result is not None,
                    "actual": step.get("actual"),
                    "error": result["error"] if result else None,
                    "stdout": result["stdout"] if result else "",
                    "ms": result.get("ms") if result else None,
                }
            )
    return shown, counts, all_passed


def _execute(session_id: int, body: CodeBody, kind: str) -> dict:
    with db.connect() as conn:
        row = al.get(conn, session_id)
        al.save_code(conn, row, body.code, body.scratch)
        row = al.get(conn, session_id)
    problem = _problem(row["problem_id"])
    tests = algorithms.tests(problem, include_hidden=(kind == "submit"))
    run = execution.run_tests(
        _workdir(session_id), row["code"], "Solution", tests, problem.runner_options()
    )
    lint = execution.lint(row["code"], config.ALGO_RUFF_CONFIG)
    shown, counts, all_passed = _summarize(tests, run)
    with db.connect() as conn:
        row = al.get(conn, session_id)
        solved = al.record_submission(conn, row, kind, all_passed, counts, len(lint["issues"]))
        row = al.get(conn, session_id)
    return {
        "kind": kind,
        "all_passed": all_passed,
        "import_error": run.import_error,
        "import_stdout": run.import_stdout,
        "crashed": run.crashed,
        "timed_out": run.timed_out,
        "stopped": run.stopped,  # a test hit its time limit; the tests after it didn't run
        "ms": run.ms,
        "shown": shown,
        "counts": counts,  # hidden tests: counts only, never inputs or outputs
        "lint": lint,
        "solved": solved,  # this submit solved it for the first time
        "solved_at": row["solved_at"],
        "timer": timer_state(row),
    }


# -- problems ----------------------------------------------------------------------------
@router.get("/problems")
def list_problems() -> dict:
    found = algorithms.list_problems()
    stats: dict[str, dict] = {}
    with db.connect() as conn:
        for row in conn.execute("SELECT * FROM algo_sessions"):
            s = stats.setdefault(
                row["problem_id"],
                {"attempts": 0, "solved": False, "solved_in_time": False, "best_time": None},
            )
            s["attempts"] += 1
            if row["solved_at"] is not None:
                s["solved"] = True
                s["solved_in_time"] |= row["solved_at"] <= row["time_limit"]
                if s["best_time"] is None or row["solved_at"] < s["best_time"]:
                    s["best_time"] = row["solved_at"]
    empty = {"attempts": 0, "solved": False, "solved_in_time": False, "best_time": None}
    return {
        "problems": [{**p.public(), **stats.get(p.id, empty)} for p in found],
        "minutes": config.ALGO_MINUTES,
        "patterns": sorted({pattern for p in found for pattern in p.patterns}),
    }


STUDY_VIEWS = ("question", "hints", "solution")


@router.get("/problems/{problem_id}/{kind}")
def study(problem_id: str, kind: str) -> dict:
    """The question, hints or the solution (explanation and commented code) outside a session.

    Refused while a session on this problem is running, so a live timed attempt can't peek.
    """
    if kind not in STUDY_VIEWS:
        raise HTTPException(404, f"Unknown view {kind!r}")
    problem = _problem(problem_id)
    with db.connect() as conn:
        live = al.active(conn)
    if live is not None and live["problem_id"] == problem.id:
        raise SessionError("This problem is in a running session. End the session to open it.")
    out: dict = {"problem": problem.public(), "kind": kind}
    if kind == "question":
        out.update(_question(problem))
    else:
        out["foundations"] = algorithms.foundation_links(problem)
        out["hints_html"] = algorithms.hints_html(problem)
        if kind == "solution":
            out["explanation_html"] = algorithms.explanation_html(problem)
    return out


# -- foundations (study pages) -----------------------------------------------------------
@router.get("/foundations")
def list_foundations() -> dict:
    return {"pages": [p.card() for p in pages.list_pages(algorithms.foundations_dir())]}


@router.get("/foundations/{slug}")
def get_foundation(slug: str) -> dict:
    try:
        return pages.payload(algorithms.foundations_dir(), slug)
    except pages.PageNotFound:
        raise HTTPException(404, f"Unknown page {slug!r}") from None


# -- sessions ----------------------------------------------------------------------------
@router.get("/active")
def get_active() -> dict:
    with db.connect() as conn:
        row = al.active(conn)
        if row is None:
            return {"session": None}
        return {
            "session": {
                "id": row["id"],
                "problem": _problem(row["problem_id"]).public(),
                "mode": row["mode"],
                "solved_at": row["solved_at"],
                "timer": timer_state(row),
            }
        }


@router.post("/sessions")
def start(body: StartBody) -> dict:
    available = algorithms.list_problems()
    if not available:
        raise HTTPException(500, "No algorithm problems are built. Run tools/build_algo.py.")
    with db.connect() as conn:
        if body.problem_id is None:
            pool = [
                p
                for p in available
                if body.difficulty in (None, p.difficulty)
                and (body.pattern is None or body.pattern in p.patterns)
            ]
            if not pool:
                raise HTTPException(400, "No problem matches those filters.")
            if body.prefer_unseen:
                seen = {r[0] for r in conn.execute("SELECT DISTINCT problem_id FROM algo_sessions")}
                pool = [p for p in pool if p.id not in seen] or pool
            problem = random.choice(pool)
        else:
            problem = _problem(body.problem_id)
        session_id = al.create(
            conn,
            problem.id,
            body.mode,
            problem.time_limit,
            algorithms.starter_code(problem),
            algorithms.scratch_starter(problem),
        )
        return _payload(al.get(conn, session_id))


@router.get("/sessions/{session_id}")
def get_session(session_id: int) -> dict:
    with db.connect() as conn:
        row = al.get(conn, session_id)
        if row["status"] != "active":
            raise SessionError("This session has ended; open its review instead.", 410)
        return _payload(row)


@router.get("/sessions/{session_id}/timer")
def get_timer(session_id: int) -> dict:
    with db.connect() as conn:
        return timer_state(al.get(conn, session_id))


@router.put("/sessions/{session_id}/code")
def save_code(session_id: int, body: CodeBody) -> dict:
    with db.connect() as conn:
        al.save_code(conn, al.get(conn, session_id), body.code, body.scratch)
        return {"ok": True, "timer": timer_state(al.get(conn, session_id))}


@router.post("/sessions/{session_id}/pause")
def pause(session_id: int) -> dict:
    with db.connect() as conn:
        al.pause(conn, al.get(conn, session_id))
        return timer_state(al.get(conn, session_id))


@router.post("/sessions/{session_id}/resume")
def resume(session_id: int) -> dict:
    with db.connect() as conn:
        al.resume(conn, al.get(conn, session_id))
        return timer_state(al.get(conn, session_id))


@router.post("/sessions/{session_id}/run")
def run(session_id: int, body: CodeBody) -> dict:
    return _execute(session_id, body, "run")


@router.post("/sessions/{session_id}/submit")
def submit(session_id: int, body: CodeBody) -> dict:
    return _execute(session_id, body, "submit")


@router.post("/sessions/{session_id}/scratch")
def scratch(session_id: int, body: CodeBody) -> dict:
    with db.connect() as conn:
        row = al.get(conn, session_id)
        al.save_code(conn, row, body.code, body.scratch)
        row = al.get(conn, session_id)
    helpers = {"helpers.py": HELPERS_SOURCE.read_text(encoding="utf-8")}
    return execution.run_scratch(_workdir(session_id), row["code"], row["scratch"], helpers)


@router.post("/sessions/{session_id}/lint")
def lint(session_id: int, body: CodeBody) -> dict:
    with db.connect() as conn:
        al.get(conn, session_id)
    return execution.lint(body.code or "", config.ALGO_RUFF_CONFIG)


@router.post("/sessions/{session_id}/end")
def end(session_id: int, body: CodeBody | None = None) -> dict:
    with db.connect() as conn:
        row = al.get(conn, session_id)
        if body is not None and row["paused_at"] is None and row["status"] == "active":
            al.save_code(conn, row, body.code, body.scratch)
            row = al.get(conn, session_id)
        al.finish(conn, row)
    return {"ok": True, "id": session_id}


# -- review & history --------------------------------------------------------------------
@router.get("/sessions/{session_id}/review")
def review(session_id: int) -> dict:
    with db.connect() as conn:
        row = al.get(conn, session_id)
        if row["status"] != "finished":
            raise SessionError("The review (hints, explanation, solution) opens when it ends.")
        problem = _problem(row["problem_id"])
        return {
            "id": row["id"],
            "problem": problem.public(),
            "mode": row["mode"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "results": al.results(conn, row),
            "pauses": al.pauses(conn, row["id"]),
            "submissions": al.submissions(conn, row["id"]),
            **_question(problem),
            "hints_html": algorithms.hints_html(problem),
            "explanation_html": algorithms.explanation_html(problem),
            "foundations": algorithms.foundation_links(problem),
            "code": row["code"],
        }


@router.get("/history")
def history() -> dict:
    by_id = {p.id: p for p in algorithms.list_problems()}
    out = []
    with db.connect() as conn:
        for row in conn.execute("SELECT * FROM algo_sessions ORDER BY id DESC").fetchall():
            problem = by_id.get(row["problem_id"])
            res = al.results(conn, row)
            out.append(
                {
                    "id": row["id"],
                    "problem_id": row["problem_id"],
                    "problem_title": problem.title if problem else row["problem_id"],
                    "difficulty": problem.difficulty if problem else None,
                    "mode": row["mode"],
                    "status": row["status"],
                    "started_at": row["started_at"],
                    "elapsed": res["elapsed"],
                    "time_limit": res["time_limit"],
                    "solved_at": res["solved_at"],
                    "timed": res["timed"],
                    "final": res["final"],
                    "pauses": res["pauses"],
                }
            )
    return {"sessions": out}
