"""End-to-end checks over the real problem set in problems/ (not the fixture)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from swe_prac import config, execution, problems

REAL = problems.list_problems()


@pytest.fixture
def real_client(tmp_path, monkeypatch, clock):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    from swe_prac.app import app

    with TestClient(app) as c:
        yield c


def test_all_seven_problems_are_built():
    assert [p.number for p in REAL] == [1, 2, 3, 4, 5, 6, 7]


@pytest.mark.parametrize("problem", REAL, ids=lambda p: p.id)
def test_reference_clears_all_levels_through_the_api(real_client, problem):
    reference = problems.reference_code(problem)
    hidden = [
        t
        for t in json.loads((problem.path / "tests.json").read_text(encoding="utf-8"))["tests"]
        if t["visibility"] == "hidden"
    ]

    start = real_client.post("/api/sessions", json={"problem_id": problem.id, "mode": "strict"})
    assert start.status_code == 200, start.text
    session = start.json()
    sid = session["id"]
    assert session["levels"][0]["statement_html"].strip()

    # The starter imports cleanly and fails with NotImplementedError, not a crash.
    run = real_client.post(f"/api/sessions/{sid}/run", json={}).json()
    assert run["import_error"] is None and not run["all_passed"]
    assert "NotImplementedError" in run["shown"][0]["error"]

    for level in (1, 2, 3, 4):
        res = real_client.post(f"/api/sessions/{sid}/submit", json={"code": reference})
        raw = res.text
        body = res.json()
        assert body["all_passed"], (level, body["breakdown"], body["import_error"])
        assert body["unlocked"]["completed"] == level
        for t in hidden:  # hidden tests: never ids or names, only counts
            assert f'"{t["id"]}"' not in raw
            assert t["name"] not in raw or len(t["name"]) < 12
        counts = body["breakdown"][str(level)]
        assert counts["hidden_total"] >= 8 and counts["shown_total"] >= 3

    assert real_client.post(f"/api/sessions/{sid}/end").status_code == 200
    review = real_client.get(f"/api/sessions/{sid}/review").json()
    assert review["results"]["timed"]["levels_completed"] == 4
    assert review["hints_html"].strip() and review["analysis_html"].strip()
    assert all(lv["statement_html"].strip() for lv in review["levels"])


@pytest.mark.parametrize("problem", REAL, ids=lambda p: p.id)
def test_starter_and_stubs_are_lint_clean(problem):
    """The code handed to the user shouldn't open with lint noise."""
    code = problems.starter_code(problem)
    for level in (2, 3, 4):
        code = code.rstrip() + "\n\n" + problems.level_stubs(problem, level)
    issues = execution.lint(code)["issues"]
    assert issues == [], issues
