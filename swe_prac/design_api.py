"""HTTP API for system design practice, mounted under /api/design.

The reference design, hints and key points stay off the session payload: they appear on the
review page, or on the study page while no session on that question is running.
"""

from __future__ import annotations

import random

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import config, db, designs, pages
from . import design_sessions as ds
from .sessions import SessionError, timer_state

router = APIRouter(prefix="/api/design")


class StartBody(BaseModel):
    question_id: str | None = None  # None means random
    mode: str
    prefer_unseen: bool = True


class NotesBody(BaseModel):
    notes: dict[str, str] | None = None
    diagram: dict | None = None


class StepBody(BaseModel):
    step: int


class AssessmentBody(BaseModel):
    checklist: list[int] = []
    key_points: list[int] = []


# -- helpers -----------------------------------------------------------------------------
def _question(question_id: str) -> designs.Question:
    try:
        return designs.get(question_id)
    except designs.QuestionNotFound:
        raise HTTPException(404, f"Unknown question {question_id!r}") from None


def _sizes(question: designs.Question) -> tuple[int, int]:
    return len(designs.checklist()), len(question.key_points)


def _payload(conn, row) -> dict:
    question = _question(row["question_id"])
    return {
        "id": row["id"],
        "question": question.public(),
        "mode": row["mode"],
        "status": row["status"],
        "current_step": row["current_step"],
        "steps": designs.steps(),
        "step_starts": {str(k): v for k, v in ds.step_starts(conn, row["id"]).items()},
        "notes": ds.notes(row),
        "diagram": ds.diagram(row),
        "timer": timer_state(row),
    }


# -- questions ---------------------------------------------------------------------------
@router.get("/questions")
def list_questions() -> dict:
    questions = designs.list_questions()
    by_id = {q.id: q for q in questions}
    attempts: dict[str, int] = {}
    best: dict[str, dict] = {}
    with db.connect() as conn:
        for row in conn.execute("SELECT * FROM design_sessions"):
            qid = row["question_id"]
            attempts[qid] = attempts.get(qid, 0) + 1
            if qid not in by_id:
                continue
            got = ds.score(row, _sizes(by_id[qid]))
            if got and (qid not in best or got["done"] > best[qid]["done"]):
                best[qid] = got
    return {
        "questions": [
            {**q.public(), "attempts": attempts.get(q.id, 0), "best": best.get(q.id)}
            for q in questions
        ],
        "time_limit": config.DESIGN_TIME_LIMIT_SECONDS,
        "steps": designs.steps(),
    }


@router.get("/framework")
def framework() -> dict:
    return {
        **designs.framework(),
        "time_limit": config.DESIGN_TIME_LIMIT_SECONDS,
        "guide_html": designs.guide_html("framework"),
        "walkthrough_html": designs.guide_html("walkthrough"),
    }


# -- foundations (study pages) -----------------------------------------------------------
@router.get("/foundations")
def list_foundations() -> dict:
    return {"pages": [p.card() for p in pages.list_pages(designs.foundations_dir())]}


@router.get("/foundations/{slug}")
def get_foundation(slug: str) -> dict:
    try:
        return pages.payload(designs.foundations_dir(), slug)
    except pages.PageNotFound:
        raise HTTPException(404, f"Unknown page {slug!r}") from None


STUDY_VIEWS = ("hints", "reference")


@router.get("/questions/{question_id}/{kind}")
def study(question_id: str, kind: str) -> dict:
    """Hints or the reference design outside a session; refused while that question is running."""
    if kind not in STUDY_VIEWS:
        raise HTTPException(404, f"Unknown view {kind!r}")
    question = _question(question_id)
    with db.connect() as conn:
        live = ds.active(conn)
    if live is not None and live["question_id"] == question.id:
        raise SessionError("This question is in a running session. End the session to open it.")
    out: dict = {"question": question.public(), "kind": kind, "hints": question.hints()}
    if kind == "reference":
        out["reference_html"] = designs.reference_html(question)
        out["key_points"] = list(question.key_points)
    return out


# -- sessions ----------------------------------------------------------------------------
@router.get("/active")
def get_active() -> dict:
    with db.connect() as conn:
        row = ds.active(conn)
        if row is None:
            return {"session": None}
        return {
            "session": {
                "id": row["id"],
                "question": _question(row["question_id"]).public(),
                "mode": row["mode"],
                "current_step": row["current_step"],
                "timer": timer_state(row),
            }
        }


@router.post("/sessions")
def start(body: StartBody) -> dict:
    available = designs.list_questions()
    if not available:
        raise HTTPException(500, "No system design questions found in designs/.")
    with db.connect() as conn:
        if body.question_id is None:
            pool = available
            if body.prefer_unseen:
                seen = {
                    r[0] for r in conn.execute("SELECT DISTINCT question_id FROM design_sessions")
                }
                pool = [q for q in available if q.id not in seen] or available
            question = random.choice(pool)
        else:
            question = _question(body.question_id)
        session_id = ds.create(conn, question.id, body.mode, designs.starter_notes())
        return _payload(conn, ds.get(conn, session_id))


@router.get("/sessions/{session_id}")
def get_session(session_id: int) -> dict:
    with db.connect() as conn:
        row = ds.get(conn, session_id)
        if row["status"] != "active":
            raise SessionError("This session has ended; open its review instead.", 410)
        return _payload(conn, row)


@router.get("/sessions/{session_id}/timer")
def get_timer(session_id: int) -> dict:
    with db.connect() as conn:
        return timer_state(ds.get(conn, session_id))


@router.put("/sessions/{session_id}/notes")
def save_notes(session_id: int, body: NotesBody) -> dict:
    with db.connect() as conn:
        ds.save(conn, ds.get(conn, session_id), body.notes, body.diagram, len(designs.steps()))
        return {"ok": True, "timer": timer_state(ds.get(conn, session_id))}


@router.post("/sessions/{session_id}/step")
def start_step(session_id: int, body: StepBody) -> dict:
    with db.connect() as conn:
        ds.start_step(conn, ds.get(conn, session_id), body.step, len(designs.steps()))
        return _payload(conn, ds.get(conn, session_id))


@router.post("/sessions/{session_id}/pause")
def pause(session_id: int) -> dict:
    with db.connect() as conn:
        ds.pause(conn, ds.get(conn, session_id))
        return timer_state(ds.get(conn, session_id))


@router.post("/sessions/{session_id}/resume")
def resume(session_id: int) -> dict:
    with db.connect() as conn:
        ds.resume(conn, ds.get(conn, session_id))
        return timer_state(ds.get(conn, session_id))


@router.post("/sessions/{session_id}/end")
def end(session_id: int, body: NotesBody | None = None) -> dict:
    with db.connect() as conn:
        row = ds.get(conn, session_id)
        if body is not None and row["paused_at"] is None and row["status"] == "active":
            ds.save(conn, row, body.notes, body.diagram, len(designs.steps()))
            row = ds.get(conn, session_id)
        ds.finish(conn, row)
    return {"ok": True, "id": session_id}


# -- review & history --------------------------------------------------------------------
@router.get("/sessions/{session_id}/review")
def review(session_id: int) -> dict:
    with db.connect() as conn:
        row = ds.get(conn, session_id)
        if row["status"] != "finished":
            raise SessionError(
                "The review (reference design, self-check) opens when the session ends."
            )
        question = _question(row["question_id"])
        steps = designs.steps()
        return {
            "id": row["id"],
            "question": question.public(),
            "hints": question.hints(),
            "mode": row["mode"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "results": ds.results(conn, row, steps),
            "pauses": ds.pauses(conn, row["id"]),
            "steps": steps,
            "notes": ds.notes(row),
            "diagram": ds.diagram(row),
            "checklist": designs.checklist(),
            "key_points": list(question.key_points),
            "assessment": ds.assessment(row),
            "score": ds.score(row, _sizes(question)),
            "reference_html": designs.reference_html(question),
        }


@router.put("/sessions/{session_id}/assessment")
def save_assessment(session_id: int, body: AssessmentBody) -> dict:
    with db.connect() as conn:
        row = ds.get(conn, session_id)
        sizes = _sizes(_question(row["question_id"]))
        picked = ds.save_assessment(conn, row, body.checklist, body.key_points, sizes)
        return {"assessment": picked, "score": ds.score(ds.get(conn, session_id), sizes)}


@router.get("/history")
def history() -> dict:
    by_id = {q.id: q for q in designs.list_questions()}
    steps = designs.steps()
    out = []
    with db.connect() as conn:
        for row in conn.execute("SELECT * FROM design_sessions ORDER BY id DESC").fetchall():
            question = by_id.get(row["question_id"])
            res = ds.results(conn, row, steps)
            out.append(
                {
                    "id": row["id"],
                    "question_id": row["question_id"],
                    "question_title": question.title if question else row["question_id"],
                    "mode": row["mode"],
                    "status": row["status"],
                    "started_at": row["started_at"],
                    "elapsed": res["elapsed"],
                    "time_limit": res["time_limit"],
                    "steps_reached": res["steps_reached"],
                    "step_count": len(steps),
                    "pauses": res["pauses"],
                    "score": ds.score(row, _sizes(question)) if question else None,
                }
            )
    return {"sessions": out}
