"""Algorithm sessions over HTTP, against the fixture problems (x01 Easy, 20 min; x02 Medium)."""

from __future__ import annotations

import json
import unittest

from support import ClientCase

from swe_prac import config

PAIR = "x01_pair_sum"
LIST = "x02_reverse_list"

GOOD = """class Solution:
    def pairSum(self, nums, target):
        seen = {}
        for i, x in enumerate(nums):
            if target - x in seen:
                return [seen[target - x], i]
            seen[x] = i
        return []
"""

# Passes both examples but only one of the three hidden tests: it only tries neighbours.
NEIGHBOURS = """class Solution:
    def pairSum(self, nums, target):
        for i in range(len(nums) - 1):
            if nums[i] + nums[i + 1] == target:
                return [i, i + 1]
        return []
"""

# Hangs on one input: the runner abandons the call at its limit (with grace) and stops.
SLEEPY = """import time


class Solution:
    def pairSum(self, nums, target):
        if nums == [1, 2]:
            time.sleep(5)
        return [0, 1]
"""


class AlgoApiTests(ClientCase):
    def _start(self, problem_id=PAIR, mode="pausable"):
        res = self.client.post("/api/algo/sessions", json={"problem_id": problem_id, "mode": mode})
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()

    def _post(self, sid, action, **body):
        return self.client.post(f"/api/algo/sessions/{sid}/{action}", json=body)

    def _end(self, sid, **body):
        res = self._post(sid, "end", **body)
        self.assertEqual(res.status_code, 200, res.text)

    def test_problem_list_and_foundations_pages(self):
        data = self.client.get("/api/algo/problems").json()
        self.assertEqual([p["id"] for p in data["problems"]], [PAIR, LIST])
        first = data["problems"][0]
        self.assertEqual(
            (first["difficulty"], first["minutes"], first["method"]), ("Easy", 20, "pairSum")
        )
        self.assertEqual((first["attempts"], first["solved"], first["best_time"]), (0, False, None))
        self.assertEqual(data["patterns"], ["Hashing", "Linked lists", "Two pointers"])
        self.assertEqual(data["minutes"], {"Easy": 20, "Medium": 30, "Hard": 40})

        cards = self.client.get("/api/algo/foundations").json()["pages"]
        self.assertEqual([(c["slug"], c["title"]) for c in cards], [("basics", "Basics")])
        page = self.client.get("/api/algo/foundations/basics").json()
        self.assertEqual([s["id"] for s in page["toc"]], ["hashing", "two-pointers"])
        self.assertEqual(page["toc"][0]["children"][0]["id"], "sets-and-maps")
        self.assertIn('id="sets-and-maps"', page["html"])
        self.assertEqual(self.client.get("/api/algo/foundations/nope").status_code, 404)

    def test_start_shows_the_question_and_examples_but_no_answers(self):
        s = self._start()
        self.assertEqual(s["params"], ["nums", "target"])
        self.assertEqual([e["expect"] for e in s["examples"]], [[0, 1], [1, 2]])
        self.assertIn("add up to", s["statement_html"])
        self.assertIn("def pairSum(self, nums: list[int], target: int) -> list[int]:", s["code"])
        self.assertIn("result = Solution().pairSum(nums, target)", s["scratch"])
        self.assertEqual(s["timer"]["limit"], 20 * 60)
        self.assertIsNone(s["solved_at"])
        text = json.dumps(s)
        for spoiler in ("secret", "Remember the numbers", "seen[target - x]", "The idea"):
            self.assertNotIn(spoiler, text)

    def test_run_checks_the_examples_only(self):
        sid = self._start()["id"]
        res = self._post(sid, "run", code=GOOD).json()
        self.assertEqual(res["kind"], "run")
        self.assertTrue(res["all_passed"])
        self.assertEqual([t["passed"] for t in res["shown"]], [True, True])
        self.assertEqual(res["shown"][0]["actual"], "[0, 1]")
        self.assertEqual((res["counts"]["shown_total"], res["counts"]["hidden_total"]), (2, 0))
        self.assertFalse(res["solved"])  # only a submit can solve

    def test_submit_reports_the_hidden_tests_as_counts_only(self):
        sid = self._start()["id"]
        res = self._post(sid, "submit", code=NEIGHBOURS).json()
        self.assertFalse(res["all_passed"])
        self.assertEqual(
            res["counts"],
            {
                "shown_passed": 2,
                "shown_total": 2,
                "hidden_passed": 1,
                "hidden_total": 3,
                "too_slow": 0,
            },
        )
        self.assertEqual(len(res["shown"]), 2)
        self.assertNotIn("secret", json.dumps(res))
        self.assertFalse(res["solved"])
        self.assertIsNone(res["solved_at"])

    def test_a_too_slow_hidden_test_is_counted_and_stops_the_run(self):
        path = config.ALGO_DIR / PAIR / "tests.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        slow = {
            "id": "h0",
            "name": "secret slow",
            "args": [[1, 2], 3],
            "expect": [0, 1],
            "limit_ms": 100,
        }
        data["hidden"].insert(0, slow)
        path.write_text(json.dumps(data), encoding="utf-8")
        sid = self._start()["id"]
        res = self._post(sid, "submit", code=SLEEPY).json()
        self.assertTrue(res["stopped"].startswith("Too slow"))
        self.assertEqual(res["counts"]["too_slow"], 1)
        self.assertEqual((res["counts"]["hidden_passed"], res["counts"]["hidden_total"]), (0, 4))
        self.assertNotIn("secret", json.dumps(res))

    def test_the_first_passing_submit_solves_the_problem(self):
        sid = self._start()["id"]
        self.clock.advance(120)
        res = self._post(sid, "submit", code=GOOD).json()
        self.assertTrue(res["all_passed"])
        self.assertTrue(res["solved"])
        self.assertEqual(res["solved_at"], 120)
        self.clock.advance(30)
        again = self._post(sid, "submit", code=GOOD).json()
        self.assertFalse(again["solved"])  # it already was
        self.assertEqual(again["solved_at"], 120)
        self.assertEqual(self.client.get(f"/api/algo/sessions/{sid}").json()["solved_at"], 120)
        listed = self.client.get("/api/algo/problems").json()["problems"][0]
        self.assertEqual(
            (listed["attempts"], listed["solved"], listed["solved_in_time"], listed["best_time"]),
            (1, True, True, 120),
        )

    def test_review_separates_the_timed_result_from_overtime(self):
        sid = self._start()["id"]
        self.clock.advance(60)
        self._post(sid, "submit", code=NEIGHBOURS)
        self.clock.advance(20 * 60)  # past the 20-minute limit
        self._post(sid, "submit", code=GOOD)
        self.assertEqual(self.client.get(f"/api/algo/sessions/{sid}/review").status_code, 409)
        self._end(sid)
        review = self.client.get(f"/api/algo/sessions/{sid}/review").json()
        r = review["results"]
        self.assertFalse(r["timed"]["solved"])
        self.assertEqual(
            r["timed"]["best"], {"passed": 3, "total": 5, "elapsed": 60, "too_slow": 0}
        )
        self.assertTrue(r["final"]["solved"])
        self.assertEqual(r["final"]["best"]["passed"], 5)
        self.assertEqual(r["overtime_seconds"], 60)
        self.assertEqual((r["runs"], r["submits"]), (0, 2))
        self.assertEqual([s["kind"] for s in review["submissions"]], ["submit", "submit"])
        self.assertIn("Remember the numbers", review["hints_html"])
        self.assertIn("ds-figure", review["explanation_html"])  # the array diagram
        self.assertIn("seen[target - x]", review["solution_code"])
        self.assertEqual(
            [f["href"] for f in review["foundations"]],
            ["#/algo/learn/basics/hashing", "#/algo/learn/basics"],
        )
        self.assertEqual(review["code"], GOOD)

    def test_study_views_are_shut_while_that_problem_is_running(self):
        hints = self.client.get(f"/api/algo/problems/{PAIR}/hints").json()
        self.assertIn("Hint 1", hints["hints_html"])
        self.assertNotIn("solution_code", hints)
        self.assertEqual(hints["foundations"][0]["title"], "Hashing")
        solution = self.client.get(f"/api/algo/problems/{PAIR}/solution").json()
        self.assertIn("seen[target - x]", solution["solution_code"])
        self.assertIn("The idea", solution["explanation_html"])
        question = self.client.get(f"/api/algo/problems/{PAIR}/question").json()
        self.assertEqual(len(question["examples"]), 2)
        self.assertEqual(self.client.get(f"/api/algo/problems/{PAIR}/bogus").status_code, 404)
        self.assertEqual(self.client.get("/api/algo/problems/nope/hints").status_code, 404)

        sid = self._start()["id"]
        for kind in ("question", "hints", "solution"):
            res = self.client.get(f"/api/algo/problems/{PAIR}/{kind}")
            self.assertEqual(res.status_code, 409, kind)
        self.assertEqual(self.client.get(f"/api/algo/problems/{LIST}/hints").status_code, 200)
        self._end(sid)
        self.assertEqual(self.client.get(f"/api/algo/problems/{PAIR}/solution").status_code, 200)

    def test_pause_blocks_work_and_strict_cannot_pause(self):
        sid = self._start()["id"]
        self.assertEqual(self._post(sid, "pause").status_code, 200)
        put = self.client.put(f"/api/algo/sessions/{sid}/code", json={"code": "x"})
        self.assertEqual(put.status_code, 409)
        self.assertEqual(self._post(sid, "run", code=GOOD).status_code, 409)
        self.clock.advance(300)
        self.assertEqual(self._post(sid, "resume").json()["elapsed"], 0)
        self._end(sid)
        strict = self._start(mode="strict")["id"]
        self.assertEqual(self._post(strict, "pause").status_code, 409)

    def test_one_active_session_and_random_start_filters(self):
        res = self.client.post(
            "/api/algo/sessions", json={"mode": "strict", "difficulty": "Medium"}
        )
        self.assertEqual(res.json()["problem"]["id"], LIST)
        self.assertEqual(
            self.client.post("/api/algo/sessions", json={"mode": "strict"}).status_code, 409
        )
        self._end(res.json()["id"])
        res = self.client.post("/api/algo/sessions", json={"mode": "strict", "pattern": "Hashing"})
        self.assertEqual(res.json()["problem"]["id"], PAIR)
        self._end(res.json()["id"])
        hard = self.client.post("/api/algo/sessions", json={"mode": "strict", "difficulty": "Hard"})
        self.assertEqual(hard.status_code, 400)
        relaxed = self.client.post(
            "/api/algo/sessions", json={"problem_id": PAIR, "mode": "relaxed"}
        )
        self.assertEqual(relaxed.status_code, 400)

    def test_random_start_prefers_problems_not_tried_yet(self):
        self._end(self._start(PAIR)["id"])
        res = self.client.post("/api/algo/sessions", json={"mode": "strict"}).json()
        self.assertEqual(res["problem"]["id"], LIST)

    def test_scratch_runs_with_the_list_helpers(self):
        s = self._start(LIST)
        self.assertIn("from helpers import make_list, list_values", s["scratch"])
        self.assertIn("class ListNode:", s["code"])
        identity = s["code"].replace("        pass\n", "        return head\n")
        res = self._post(s["id"], "scratch", code=identity).json()
        self.assertEqual(res["exit_code"], 0, res["stderr"])
        self.assertIn("[1, 2, 3]", res["stdout"])

    def test_lint_allows_the_problems_camel_case_names(self):
        sid = self._start()["id"]
        code = (
            "import os\n\n\nclass Solution:\n"
            "    def pairSum(self, numList, target):\n        return []\n"
        )
        codes = {i["code"] for i in self._post(sid, "lint", code=code).json()["issues"]}
        self.assertIn("F401", codes)  # unused import
        self.assertFalse(codes & {"N802", "N803"}, codes)

    def test_end_saves_the_code_and_history_lists_the_session(self):
        sid = self._start()["id"]
        self.clock.advance(90)
        self._end(sid, code=GOOD)
        self.assertEqual(self.client.get(f"/api/algo/sessions/{sid}").status_code, 410)
        (row,) = self.client.get("/api/algo/history").json()["sessions"]
        self.assertEqual(
            (row["problem_title"], row["difficulty"], row["status"], row["elapsed"]),
            ("Pair Sum (test fixture)", "Easy", "finished", 90),
        )
        self.assertFalse(row["final"]["solved"])
        self.assertEqual(self.client.get(f"/api/algo/sessions/{sid}/review").json()["code"], GOOD)


if __name__ == "__main__":
    unittest.main()
