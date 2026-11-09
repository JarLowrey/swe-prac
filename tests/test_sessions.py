from __future__ import annotations

import pytest

from swe_prac import db, sessions
from swe_prac.sessions import SessionError


@pytest.fixture
def conn(env, clock):
    db.init()
    with db.connect() as c:
        yield c


def _new(conn, mode="pausable"):
    return sessions.get(conn, sessions.create(conn, "p0_counter", mode, "code"))


def test_elapsed_excludes_pauses(conn, clock):
    row = _new(conn)
    clock.advance(100)
    sessions.pause(conn, row)
    clock.advance(1000)  # paused time doesn't count
    row = sessions.get(conn, row["id"])
    assert sessions.elapsed(row) == pytest.approx(100)
    sessions.resume(conn, row)
    clock.advance(50)
    row = sessions.get(conn, row["id"])
    assert sessions.elapsed(row) == pytest.approx(150)
    assert sessions.pauses(conn, row["id"])[0]["ended_at"] is not None


def test_strict_cannot_pause_and_one_active_session(conn):
    row = _new(conn, "strict")
    with pytest.raises(SessionError, match="strict"):
        sessions.pause(conn, row)
    with pytest.raises(SessionError, match="active session"):
        sessions.create(conn, "p0_counter", "pausable", "code")


def test_cannot_pause_in_overtime_or_edit_while_paused(conn, clock):
    row = _new(conn)
    sessions.pause(conn, row)
    with pytest.raises(SessionError, match="paused"):
        sessions.save_code(conn, sessions.get(conn, row["id"]), "x", None)
    sessions.resume(conn, sessions.get(conn, row["id"]))
    clock.advance(90 * 60 + 1)
    with pytest.raises(SessionError, match="Time is up"):
        sessions.pause(conn, sessions.get(conn, row["id"]))


def test_results_split_timed_and_overtime(conn, clock):
    row = _new(conn, "strict")
    clock.advance(10 * 60)
    sessions.complete_level(conn, sessions.get(conn, row["id"]))  # L1 at 10:00
    clock.advance(70 * 60)
    sessions.complete_level(conn, sessions.get(conn, row["id"]))  # L2 at 80:00
    sessions.record_submission(
        conn,
        sessions.get(conn, row["id"]),
        "submit",
        3,
        False,
        {"3": {"shown_passed": 2, "shown_total": 3, "hidden_passed": 5, "hidden_total": 9}},
        0,
    )
    clock.advance(20 * 60)
    sessions.complete_level(conn, sessions.get(conn, row["id"]))  # L3 at 100:00 (overtime)
    sessions.finish(conn, sessions.get(conn, row["id"]))
    res = sessions.results(conn, sessions.get(conn, row["id"]))
    assert res["timed"]["levels_completed"] == 2
    assert res["timed"]["stopped_level"] == 3
    assert res["timed"]["stopped_level_ratio"]["passed"] == 7
    assert res["timed"]["stopped_level_ratio"]["total"] == 12
    assert res["final"]["levels_completed"] == 3
    assert res["levels"][2]["overtime"] is True
    assert res["levels"][1]["split"] == pytest.approx(70 * 60)
    assert res["overtime_seconds"] == pytest.approx(10 * 60)


def test_finish_while_paused_closes_pause(conn, clock):
    row = _new(conn)
    clock.advance(30)
    sessions.pause(conn, row)
    clock.advance(500)
    sessions.finish(conn, sessions.get(conn, row["id"]))
    row = sessions.get(conn, row["id"])
    assert row["status"] == "finished"
    assert sessions.elapsed(row) == pytest.approx(30)
