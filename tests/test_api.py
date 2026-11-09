from __future__ import annotations

from conftest import COUNTER_FULL

L1_ONLY = """
class Counter:
    def __init__(self):
        self.counts = {}

    def incr(self, timestamp, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]
"""


def _start(client, mode="pausable"):
    res = client.post("/api/sessions", json={"problem_id": "p0_counter", "mode": mode})
    assert res.status_code == 200, res.text
    return res.json()


def test_start_shows_only_level_one(client):
    s = _start(client)
    assert s["current_level"] == 1
    assert [lv["level"] for lv in s["levels"]] == [1]
    assert "class Counter:" in s["code"] and "def incr" in s["code"]
    assert "def get" not in s["code"]  # later-level stubs stay hidden
    assert "Level 2" not in str(s["levels"])


def test_starter_fails_then_level_gating(client):
    sid = _start(client)["id"]
    run = client.post(f"/api/sessions/{sid}/run", json={}).json()
    assert run["all_passed"] is False
    assert "NotImplementedError" in run["shown"][0]["error"]

    res = client.post(f"/api/sessions/{sid}/submit", json={"code": L1_ONLY}).json()
    assert res["all_passed"] and res["unlocked"] == {"completed": 1, "new_level": 2}
    assert [lv["level"] for lv in res["session"]["levels"]] == [1, 2]

    # Level 2 requires get(); L1-only code fails, and stays on level 2.
    res = client.post(f"/api/sessions/{sid}/submit", json={"code": L1_ONLY}).json()
    assert not res["all_passed"] and res["unlocked"] is None
    assert res["breakdown"]["1"]["hidden_passed"] == 1  # earlier levels re-run (cumulative)

    for expected in (3, 4, 5):
        res = client.post(f"/api/sessions/{sid}/submit", json={"code": COUNTER_FULL}).json()
        assert res["unlocked"]["new_level"] == expected
    assert client.get(f"/api/sessions/{sid}").json()["all_levels_done"] is True


def test_regression_in_earlier_level_blocks_unlock(client):
    sid = _start(client)["id"]
    client.post(f"/api/sessions/{sid}/submit", json={"code": COUNTER_FULL})
    broken = COUNTER_FULL.replace("return self.counts[key]", "return 99")
    res = client.post(f"/api/sessions/{sid}/submit", json={"code": broken}).json()
    assert res["unlocked"] is None
    assert res["breakdown"]["1"]["shown_passed"] == 0


def test_hidden_test_details_never_leave_the_server(client):
    sid = _start(client)["id"]
    for code in (L1_ONLY.replace("+ 1", "+ 2"), COUNTER_FULL):
        raw = client.post(f"/api/sessions/{sid}/submit", json={"code": code}).text
        assert "SECRET-HIDDEN-NAME" not in raw
        assert "zz-secret-key" not in raw
        assert "L1-H1" not in raw


def test_run_never_includes_hidden_tests(client):
    sid = _start(client)["id"]
    res = client.post(f"/api/sessions/{sid}/run", json={"code": COUNTER_FULL}).json()
    assert res["breakdown"]["1"]["hidden_total"] == 0
    assert res["unlocked"] is None  # run never unlocks


def test_pause_blocks_work_and_strict_cannot_pause(client, clock):
    sid = _start(client)["id"]
    assert client.post(f"/api/sessions/{sid}/pause").json()["paused"] is True
    assert client.post(f"/api/sessions/{sid}/run", json={"code": "x"}).status_code == 409
    assert client.put(f"/api/sessions/{sid}/code", json={"code": "x"}).status_code == 409
    clock.advance(600)
    timer = client.post(f"/api/sessions/{sid}/resume").json()
    assert timer["paused"] is False and timer["elapsed"] < 1
    client.post(f"/api/sessions/{sid}/end")

    strict = _start(client, "strict")["id"]
    assert client.post(f"/api/sessions/{strict}/pause").status_code == 409


def test_one_active_session_and_review_lifecycle(client, clock):
    sid = _start(client)["id"]
    second = client.post("/api/sessions", json={"problem_id": "p0_counter", "mode": "strict"})
    assert second.status_code == 409
    assert client.get(f"/api/sessions/{sid}/review").status_code == 409  # no spoilers mid-session

    client.post(f"/api/sessions/{sid}/submit", json={"code": COUNTER_FULL})
    clock.advance(120)
    assert client.post(f"/api/sessions/{sid}/end", json={"code": COUNTER_FULL}).status_code == 200
    review = client.get(f"/api/sessions/{sid}/review").json()
    assert review["results"]["timed"]["levels_completed"] == 1
    assert review["code"] == COUNTER_FULL
    assert len(review["levels"]) == 4
    assert client.get(f"/api/sessions/{sid}").status_code == 410

    history = client.get("/api/history").json()["sessions"]
    assert history[0]["id"] == sid and history[0]["timed_levels"] == 1
    problems = client.get("/api/problems").json()["problems"]
    assert problems[0]["attempts"] == 1 and problems[0]["best_timed_levels"] == 1


def test_overtime_completion_not_counted_in_timed_result(client, clock):
    sid = _start(client, "strict")["id"]
    clock.advance(91 * 60)
    client.post(f"/api/sessions/{sid}/submit", json={"code": COUNTER_FULL})
    client.post(f"/api/sessions/{sid}/end")
    res = client.get(f"/api/sessions/{sid}/review").json()["results"]
    assert res["timed"]["levels_completed"] == 0
    assert res["final"]["levels_completed"] == 1


def test_random_start_prefers_unseen(client):
    s = client.post("/api/sessions", json={"problem_id": None, "mode": "strict"}).json()
    assert s["problem"]["id"] == "p0_counter"


def test_scratch_lint_format_endpoints(client):
    sid = _start(client)["id"]
    out = client.post(
        f"/api/sessions/{sid}/scratch",
        json={
            "code": COUNTER_FULL,
            "scratch": "from solution import *\nprint(Counter().incr(1, 'a'))\n",
        },
    ).json()
    assert out["stdout"].strip() == "1"
    lint = client.post(f"/api/sessions/{sid}/lint", json={"code": "import os\n"}).json()
    assert lint["issues"][0]["code"] == "F401"
    assert client.post("/api/format", json={"code": "x=1\n"}).json()["code"] == "x = 1\n"
