from __future__ import annotations

import unittest

from support import COUNTER_FULL, ClientCase

L1_ONLY = """
class Counter:
    def __init__(self):
        self.counts = {}

    def incr(self, timestamp, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]
"""


class ApiTests(ClientCase):
    def _start(self, mode="pausable"):
        res = self.client.post("/api/sessions", json={"problem_id": "p0_counter", "mode": mode})
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()

    def _post(self, sid, action, **body):
        return self.client.post(f"/api/sessions/{sid}/{action}", json=body)

    def test_start_shows_only_level_one(self):
        s = self._start()
        self.assertEqual(s["current_level"], 1)
        self.assertEqual([lv["level"] for lv in s["levels"]], [1])
        self.assertIn("class Counter:", s["code"])
        self.assertIn("def incr", s["code"])
        self.assertNotIn("def get", s["code"])  # later-level stubs stay hidden
        self.assertNotIn("Level 2", str(s["levels"]))

    def test_static_files_are_revalidated_not_cached(self):
        res = self.client.get("/static/app.js")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["cache-control"], "no-cache")

    def test_start_gives_a_tests_file_and_a_scratch_example(self):
        s = self._start()
        self.assertIn("def test_incr_counts_up(self)", s["tests_source"])
        self.assertNotIn("def test_get", s["tests_source"])  # level 2's shown test stays locked
        self.assertTrue(s["scratch"].startswith("# Scratch"))
        self.assertIn("class ExampleTest(unittest.TestCase)", s["scratch"])
        self.assertIn('counter.incr(1, "a"), 1)', s["scratch"])

    def test_tests_file_grows_with_each_unlocked_level(self):
        sid = self._start()["id"]
        res = self._post(sid, "submit", code=COUNTER_FULL).json()
        unlocked = res["session"]["tests_source"]
        self.assertIn("def test_incr_counts_up(self)", unlocked)
        self.assertIn("def test_get(self)", unlocked)
        self.assertNotIn("def test_reset(self)", unlocked)
        self.assertEqual(self.client.get(f"/api/sessions/{sid}").json()["tests_source"], unlocked)

        for _ in range(3):
            res = self._post(sid, "submit", code=COUNTER_FULL).json()
        done = res["session"]["tests_source"]
        for name in ("incr_counts_up", "get", "reset", "total"):
            self.assertIn(f"def test_{name}(self)", done)
        self.assertIn("Levels 1-4", done)

    def test_starter_fails_then_level_gating(self):
        sid = self._start()["id"]
        run = self._post(sid, "run").json()
        self.assertIs(run["all_passed"], False)
        self.assertIn("NotImplementedError", run["shown"][0]["error"])

        res = self._post(sid, "submit", code=L1_ONLY).json()
        self.assertTrue(res["all_passed"])
        self.assertEqual(res["unlocked"], {"completed": 1, "new_level": 2})
        self.assertEqual([lv["level"] for lv in res["session"]["levels"]], [1, 2])

        # Level 2 requires get(); L1-only code fails, and stays on level 2.
        res = self._post(sid, "submit", code=L1_ONLY).json()
        self.assertFalse(res["all_passed"])
        self.assertIsNone(res["unlocked"])
        self.assertEqual(res["breakdown"]["1"]["hidden_passed"], 1)  # earlier levels re-run

        for expected in (3, 4, 5):
            res = self._post(sid, "submit", code=COUNTER_FULL).json()
            self.assertEqual(res["unlocked"]["new_level"], expected)
        self.assertIs(self.client.get(f"/api/sessions/{sid}").json()["all_levels_done"], True)

    def test_regression_in_earlier_level_blocks_unlock(self):
        sid = self._start()["id"]
        self._post(sid, "submit", code=COUNTER_FULL)
        broken = COUNTER_FULL.replace("return self.counts[key]", "return 99")
        res = self._post(sid, "submit", code=broken).json()
        self.assertIsNone(res["unlocked"])
        self.assertEqual(res["breakdown"]["1"]["shown_passed"], 0)

    def test_hidden_test_details_never_leave_the_server(self):
        started = self.client.post(
            "/api/sessions", json={"problem_id": "p0_counter", "mode": "pausable"}
        )
        sid = started.json()["id"]
        leaks = ("SECRET-HIDDEN-NAME", "zz-secret-key", "L1-H1")
        # tests.py is built from shown tests only.
        self.assertFalse(any(leak in started.text for leak in leaks))
        for code in (L1_ONLY.replace("+ 1", "+ 2"), COUNTER_FULL):
            raw = self._post(sid, "submit", code=code).text
            self.assertFalse(any(leak in raw for leak in leaks))
        self.assertFalse(
            any(leak in self.client.get(f"/api/sessions/{sid}").text for leak in leaks)
        )

    def test_run_never_includes_hidden_tests(self):
        sid = self._start()["id"]
        res = self._post(sid, "run", code=COUNTER_FULL).json()
        self.assertEqual(res["breakdown"]["1"]["hidden_total"], 0)
        self.assertIsNone(res["unlocked"])  # run never unlocks

    def test_pause_blocks_work_and_strict_cannot_pause(self):
        sid = self._start()["id"]
        self.assertIs(self._post(sid, "pause").json()["paused"], True)
        self.assertEqual(self._post(sid, "run", code="x").status_code, 409)
        self.assertEqual(
            self.client.put(f"/api/sessions/{sid}/code", json={"code": "x"}).status_code, 409
        )
        self.clock.advance(600)
        timer = self._post(sid, "resume").json()
        self.assertIs(timer["paused"], False)
        self.assertLess(timer["elapsed"], 1)
        self._post(sid, "end")

        strict = self._start("strict")["id"]
        self.assertEqual(self._post(strict, "pause").status_code, 409)

    def test_one_active_session_and_review_lifecycle(self):
        sid = self._start()["id"]
        second = self.client.post(
            "/api/sessions", json={"problem_id": "p0_counter", "mode": "strict"}
        )
        self.assertEqual(second.status_code, 409)
        # No spoilers mid-session.
        self.assertEqual(self.client.get(f"/api/sessions/{sid}/review").status_code, 409)

        self._post(sid, "submit", code=COUNTER_FULL)
        self.clock.advance(120)
        self.assertEqual(self._post(sid, "end", code=COUNTER_FULL).status_code, 200)
        review = self.client.get(f"/api/sessions/{sid}/review").json()
        self.assertEqual(review["results"]["timed"]["levels_completed"], 1)
        self.assertEqual(review["code"], COUNTER_FULL)
        self.assertEqual(len(review["levels"]), 4)
        self.assertEqual(self.client.get(f"/api/sessions/{sid}").status_code, 410)

        history = self.client.get("/api/history").json()["sessions"]
        self.assertEqual(history[0]["id"], sid)
        self.assertEqual(history[0]["timed_levels"], 1)
        listed = self.client.get("/api/problems").json()["problems"]
        self.assertEqual(listed[0]["attempts"], 1)
        self.assertEqual(listed[0]["best_timed_levels"], 1)

    def test_overtime_completion_not_counted_in_timed_result(self):
        sid = self._start("strict")["id"]
        self.clock.advance(91 * 60)
        self._post(sid, "submit", code=COUNTER_FULL)
        self._post(sid, "end")
        res = self.client.get(f"/api/sessions/{sid}/review").json()["results"]
        self.assertEqual(res["timed"]["levels_completed"], 0)
        self.assertEqual(res["final"]["levels_completed"], 1)

    def test_random_start_prefers_unseen(self):
        s = self.client.post("/api/sessions", json={"problem_id": None, "mode": "strict"}).json()
        self.assertEqual(s["problem"]["id"], "p0_counter")

    def test_scratch_lint_format_endpoints(self):
        sid = self._start()["id"]
        scratch = (
            "import sys\nimport unittest\n\nfrom solution import *\n\n\n"
            "class ScratchTest(unittest.TestCase):\n"
            "    def test_incr(self):\n"
            "        self.assertEqual(Counter().incr(1, 'a'), 1)\n\n\n"
            "unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout))\n"
        )
        out = self._post(sid, "scratch", code=COUNTER_FULL, scratch=scratch).json()
        self.assertEqual(out["exit_code"], 0, out["stdout"] + out["stderr"])
        self.assertIn("OK", out["stdout"])
        lint = self._post(sid, "lint", code="import os\n").json()
        self.assertEqual(lint["issues"][0]["code"], "F401")
        self.assertEqual(
            self.client.post("/api/format", json={"code": "x=1\n"}).json()["code"], "x = 1\n"
        )

    def test_scratch_example_runs_as_a_unittest(self):
        started = self._start()
        sid, scratch, starter = started["id"], started["scratch"], started["code"]
        ok = self._post(sid, "scratch", code=COUNTER_FULL, scratch=scratch).json()
        self.assertEqual(ok["exit_code"], 0, ok["stdout"])
        self.assertIn("test_example", ok["stdout"])
        self.assertIn("OK", ok["stdout"])
        # On the unimplemented starter the example fails with NotImplementedError.
        bad = self._post(sid, "scratch", code=starter, scratch=scratch).json()
        self.assertNotEqual(bad["exit_code"], 0)
        self.assertIn("NotImplementedError", bad["stdout"] + bad["stderr"])


if __name__ == "__main__":
    unittest.main()
