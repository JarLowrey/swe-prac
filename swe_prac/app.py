"""HTTP API and static frontend."""

from __future__ import annotations

import random
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, db, execution, problems, sessions
from .sessions import SessionError


@asynccontextmanager
async def _lifespan(_: FastAPI):
    db.init()
    yield


app = FastAPI(title="SWE Practice", docs_url=None, redoc_url=None, lifespan=_lifespan)


@app.exception_handler(SessionError)
def _session_error(_: Request, exc: SessionError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=exc.status)


# -- request bodies ----------------------------------------------------------------------
class StartBody(BaseModel):
    problem_id: str | None = None  # None means random
    mode: str
    prefer_unseen: bool = True


class CodeBody(BaseModel):
    code: str | None = None
    scratch: str | None = None


class FormatBody(BaseModel):
    code: str


# -- helpers -----------------------------------------------------------------------------
def _problem(problem_id: str) -> problems.Problem:
    try:
        return problems.get(problem_id)
    except problems.ProblemNotFound:
        raise HTTPException(404, f"Unknown problem {problem_id!r}") from None


def _workdir(session_id: int) -> Path:
    return config.DATA_DIR / "sessions" / str(session_id)


def _session_payload(conn, row) -> dict:
    problem = _problem(row["problem_id"])
    done = sessions.completions(conn, row["id"])
    unlocked = min(row["current_level"], len(config.LEVELS))
    return {
        "id": row["id"],
        "problem": problem.public(),
        "mode": row["mode"],
        "status": row["status"],
        "current_level": row["current_level"],
        "all_levels_done": row["current_level"] > len(config.LEVELS),
        "levels": [
            {
                "level": lv,
                "title": problem.level_title(lv),
                "statement_html": problems.statement_html(problem, lv),
                "stubs": problems.level_stubs(problem, lv),
                "completed_at": done.get(lv),
            }
            for lv in range(1, unlocked + 1)
        ],
        "code": row["code"],
        "scratch": row["scratch"],
        "tests_source": problems.shown_tests_source(problem, unlocked),
        "timer": sessions.timer_state(row),
        "pacing": config.PACING_SECONDS,
        "conventions_html": problems.conventions_html(),
    }


def _summarize(tests: list[dict], run: execution.TestRun) -> tuple[list[dict], dict, bool]:
    """Split results into full shown-test detail and hidden-test counts per level."""
    shown, breakdown = [], {}
    all_passed = run.import_error is None and run.crashed is None
    for test in tests:
        result = run.results.get(test["id"])
        passed = bool(result and result["passed"])
        all_passed &= passed
        counts = breakdown.setdefault(
            str(test["level"]),
            {"shown_passed": 0, "shown_total": 0, "hidden_passed": 0, "hidden_total": 0},
        )
        counts[f"{test['visibility']}_total"] += 1
        counts[f"{test['visibility']}_passed"] += passed
        if test["visibility"] == "shown":
            shown.append(
                {
                    "id": test["id"],
                    "level": test["level"],
                    "name": test["name"],
                    "passed": passed,
                    "ran": result is not None,
                    "steps": result["steps"] if result else [],
                    "total_steps": len(test["steps"]),
                    "failed_step": result["failed_step"] if result else None,
                    "error": result["error"] if result else None,
                    "stdout": result["stdout"] if result else "",
                    "ms": result.get("ms") if result else None,
                }
            )
    return shown, breakdown, all_passed


def _execute(session_id: int, body: CodeBody, kind: str) -> dict:
    with db.connect() as conn:
        row = sessions.get(conn, session_id)
        sessions.save_code(conn, row, body.code, body.scratch)
        row = sessions.get(conn, session_id)
    problem = _problem(row["problem_id"])
    level = min(row["current_level"], len(config.LEVELS))
    tests = problems.tests(problem, level, include_hidden=(kind == "submit"))
    run = execution.run_tests(_workdir(session_id), row["code"], problem.class_name, tests)
    lint = execution.lint(row["code"])
    shown, breakdown, all_passed = _summarize(tests, run)

    unlocked = None
    with db.connect() as conn:
        row = sessions.get(conn, session_id)
        sessions.record_submission(
            conn, row, kind, level, all_passed, breakdown, len(lint["issues"])
        )
        if kind == "submit" and all_passed and row["current_level"] == level:
            new_level = sessions.complete_level(conn, row)
            unlocked = {"completed": level, "new_level": new_level}
        row = sessions.get(conn, session_id)
        payload = _session_payload(conn, row) if unlocked else None
    return {
        "kind": kind,
        "level": level,
        "all_passed": all_passed,
        "import_error": run.import_error,
        "import_stdout": run.import_stdout,
        "crashed": run.crashed,
        "timed_out": run.timed_out,
        "ms": run.ms,
        "shown": shown,
        "breakdown": breakdown,  # hidden tests: counts only, never inputs or outputs
        "lint": lint,
        "unlocked": unlocked,
        "session": payload,
    }


# -- problems ----------------------------------------------------------------------------
@app.get("/api/problems")
def list_problems() -> dict:
    with db.connect() as conn:
        stats = {
            r["problem_id"]: dict(r)
            for r in conn.execute(
                "SELECT problem_id, COUNT(*) AS attempts FROM sessions GROUP BY problem_id"
            )
        }
        best = {}
        for row in conn.execute("SELECT * FROM sessions WHERE status = 'finished'"):
            res = sessions.results(conn, row)
            key = row["problem_id"]
            score = res["timed"]["levels_completed"]
            best[key] = max(best.get(key, 0), score)
    return {
        "problems": [
            {
                **p.public(),
                "attempts": stats.get(p.id, {}).get("attempts", 0),
                "best_timed_levels": best.get(p.id),
            }
            for p in problems.list_problems()
        ],
        "time_limit": config.TIME_LIMIT_SECONDS,
        "pacing": config.PACING_SECONDS,
    }


# -- sessions ----------------------------------------------------------------------------
@app.get("/api/active")
def get_active() -> dict:
    with db.connect() as conn:
        row = sessions.active(conn)
        if row is None:
            return {"session": None}
        problem = _problem(row["problem_id"])
        return {
            "session": {
                "id": row["id"],
                "problem": problem.public(),
                "mode": row["mode"],
                "current_level": row["current_level"],
                "timer": sessions.timer_state(row),
            }
        }


@app.post("/api/sessions")
def start_session(body: StartBody) -> dict:
    available = problems.list_problems()
    if not available:
        raise HTTPException(500, "No problems are built. Run tools/build_problem.py --all.")
    with db.connect() as conn:
        if body.problem_id is None:
            pool = available
            if body.prefer_unseen:
                seen = {r[0] for r in conn.execute("SELECT DISTINCT problem_id FROM sessions")}
                unseen = [p for p in available if p.id not in seen]
                pool = unseen or available
            problem = random.choice(pool)
        else:
            problem = _problem(body.problem_id)
        session_id = sessions.create(
            conn,
            problem.id,
            body.mode,
            problems.starter_code(problem),
            problems.scratch_starter(problem),
        )
        return _session_payload(conn, sessions.get(conn, session_id))


@app.get("/api/sessions/{session_id}")
def get_session(session_id: int) -> dict:
    with db.connect() as conn:
        row = sessions.get(conn, session_id)
        if row["status"] != "active":
            raise SessionError("This session has ended; open its review instead.", 410)
        return _session_payload(conn, row)


@app.get("/api/sessions/{session_id}/timer")
def get_timer(session_id: int) -> dict:
    with db.connect() as conn:
        return sessions.timer_state(sessions.get(conn, session_id))


@app.put("/api/sessions/{session_id}/code")
def save_code(session_id: int, body: CodeBody) -> dict:
    with db.connect() as conn:
        row = sessions.get(conn, session_id)
        sessions.save_code(conn, row, body.code, body.scratch)
        return {"ok": True, "timer": sessions.timer_state(sessions.get(conn, session_id))}


@app.post("/api/sessions/{session_id}/pause")
def pause(session_id: int) -> dict:
    with db.connect() as conn:
        sessions.pause(conn, sessions.get(conn, session_id))
        return sessions.timer_state(sessions.get(conn, session_id))


@app.post("/api/sessions/{session_id}/resume")
def resume(session_id: int) -> dict:
    with db.connect() as conn:
        sessions.resume(conn, sessions.get(conn, session_id))
        return sessions.timer_state(sessions.get(conn, session_id))


@app.post("/api/sessions/{session_id}/run")
def run(session_id: int, body: CodeBody) -> dict:
    return _execute(session_id, body, "run")


@app.post("/api/sessions/{session_id}/submit")
def submit(session_id: int, body: CodeBody) -> dict:
    return _execute(session_id, body, "submit")


@app.post("/api/sessions/{session_id}/scratch")
def scratch(session_id: int, body: CodeBody) -> dict:
    with db.connect() as conn:
        row = sessions.get(conn, session_id)
        sessions.save_code(conn, row, body.code, body.scratch)
        row = sessions.get(conn, session_id)
    return execution.run_scratch(_workdir(session_id), row["code"], row["scratch"])


@app.post("/api/sessions/{session_id}/lint")
def lint(session_id: int, body: CodeBody) -> dict:
    with db.connect() as conn:
        sessions.get(conn, session_id)
    return execution.lint(body.code or "")


@app.post("/api/format")
def format_code(body: FormatBody) -> dict:
    return execution.format_code(body.code)


@app.post("/api/sessions/{session_id}/end")
def end(session_id: int, body: CodeBody | None = None) -> dict:
    with db.connect() as conn:
        row = sessions.get(conn, session_id)
        if body is not None and row["paused_at"] is None and row["status"] == "active":
            sessions.save_code(conn, row, body.code, body.scratch)
            row = sessions.get(conn, session_id)
        sessions.finish(conn, row)
    return {"ok": True, "id": session_id}


# -- review & history --------------------------------------------------------------------
@app.get("/api/sessions/{session_id}/review")
def review(session_id: int) -> dict:
    with db.connect() as conn:
        row = sessions.get(conn, session_id)
        if row["status"] != "finished":
            raise SessionError("Reviews (hints, analysis, reference) unlock when the session ends.")
        problem = _problem(row["problem_id"])
        return {
            "id": row["id"],
            "problem": problem.public(),
            "mode": row["mode"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "results": sessions.results(conn, row),
            "pauses": sessions.pauses(conn, row["id"]),
            "submissions": sessions.submissions(conn, row["id"]),
            "levels": [
                {
                    "level": lv,
                    "title": problem.level_title(lv),
                    "statement_html": problems.statement_html(problem, lv),
                }
                for lv in config.LEVELS
            ],
            "hints_html": problems.review_html(problem, "hints"),
            "analysis_html": problems.review_html(problem, "analysis"),
            "reference_code": problems.reference_code(problem),
            "code": row["code"],
            "conventions_html": problems.conventions_html(),
        }


@app.get("/api/history")
def history() -> dict:
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM sessions ORDER BY id DESC").fetchall()
        titles = {p.id: p.title for p in problems.list_problems()}
        out = []
        for row in rows:
            res = sessions.results(conn, row)
            out.append(
                {
                    "id": row["id"],
                    "problem_id": row["problem_id"],
                    "problem_title": titles.get(row["problem_id"], row["problem_id"]),
                    "mode": row["mode"],
                    "status": row["status"],
                    "started_at": row["started_at"],
                    "elapsed": res["elapsed"],
                    "timed_levels": res["timed"]["levels_completed"],
                    "final_levels": res["final"]["levels_completed"],
                    "pauses": res["pauses"],
                    "current_level": row["current_level"],
                }
            )
    return {"sessions": out}


# -- frontend ----------------------------------------------------------------------------
class _RevalidatedStatic(StaticFiles):
    """Always revalidate, so a browser never runs a stale app.js against a newer backend."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


app.mount("/static", _RevalidatedStatic(directory=config.STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(config.STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})
