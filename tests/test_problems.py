"""End-to-end checks over the real problem set in problems/ (not the fixture)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from contextlib import contextmanager

from support import RealClientCase, TempDirCase

from swe_prac import execution, problems

REAL = problems.list_problems()


def _all_stubs(problem) -> str:
    code = problems.starter_code(problem)
    for level in (2, 3, 4):
        code = code.rstrip() + "\n\n" + problems.level_stubs(problem, level)
    return code


class CatalogueTests(unittest.TestCase):
    def test_all_seven_problems_are_built(self):
        self.assertEqual([p.number for p in REAL], [1, 2, 3, 4, 5, 6, 7])

    def test_starter_and_stubs_are_lint_clean(self):
        """The code handed to the user shouldn't open with lint noise."""
        for problem in REAL:
            with self.subTest(problem=problem.id):
                self.assertEqual(execution.lint(_all_stubs(problem))["issues"], [])


class GeneratedTestsFileTests(TempDirCase):
    def _run_unittest_module(self, solution: str, source: str) -> subprocess.CompletedProcess:
        """Run the generated tests.py with `python -m unittest`, next to a solution.py."""
        (self.tmp_path / "solution.py").write_text(solution, encoding="utf-8")
        (self.tmp_path / "tests.py").write_text(source, encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "tests"],
            cwd=self.tmp_path,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_passes_the_reference_and_fails_the_stubs(self):
        for problem in REAL:
            with self.subTest(problem=problem.id):
                source = problems.shown_tests_source(problem, 4)
                shown = problems.tests(problem, 4, include_hidden=False)

                ok = self._run_unittest_module(problems.reference_code(problem), source)
                self.assertEqual(ok.returncode, 0, ok.stderr)
                # One test method per shown test, none dropped or merged.
                self.assertEqual(int(re.search(r"Ran (\d+) tests?", ok.stderr)[1]), len(shown))

                stubs = self._run_unittest_module(_all_stubs(problem), source)
                self.assertNotEqual(stubs.returncode, 0)
                self.assertIn("NotImplementedError", stubs.stderr)

    def test_matches_what_run_executes_and_hides_later_levels(self):
        for problem in REAL:
            data = json.loads((problem.path / "problem.json").read_text(encoding="utf-8"))
            methods = {lv["level"]: lv["methods"] for lv in data["levels"]}
            for level in (1, 2, 3, 4):
                with self.subTest(problem=problem.id, level=level):
                    source = problems.shown_tests_source(problem, level)
                    shown = problems.tests(problem, level, include_hidden=False)
                    self.assertEqual(source.count("\n    def test_"), len(shown))
                    self.assertIn(f"class Level{level}Tests(", source)
                    self.assertNotIn(f"class Level{level + 1}Tests(", source)
                    for later in range(level + 1, 5):
                        for method in methods[later]:
                            self.assertNotIn(f".{method}(", source)
                    self.assertIn("hidden tests", source)  # says where the other tests went


class RealProblemApiTests(RealClientCase):
    @contextmanager
    def _session(self, problem, mode="strict"):
        """Start a session and always end it, so one failing problem can't block the next."""
        res = self.client.post("/api/sessions", json={"problem_id": problem.id, "mode": mode})
        self.assertEqual(res.status_code, 200, res.text)
        sid = res.json()["id"]
        try:
            yield sid
        finally:
            self.client.post(f"/api/sessions/{sid}/end")

    def test_reference_clears_all_levels_through_the_api(self):
        for problem in REAL:
            with self.subTest(problem=problem.id), self._session(problem) as sid:
                self._clear_all_levels(problem, sid)

    def _clear_all_levels(self, problem, sid):
        reference = problems.reference_code(problem)
        raw_tests = json.loads((problem.path / "tests.json").read_text(encoding="utf-8"))["tests"]
        hidden = [t for t in raw_tests if t["visibility"] == "hidden"]
        session = self.client.get(f"/api/sessions/{sid}").json()
        self.assertTrue(session["levels"][0]["statement_html"].strip())

        # The starter imports cleanly and fails with NotImplementedError, not a crash.
        run = self.client.post(f"/api/sessions/{sid}/run", json={}).json()
        self.assertIsNone(run["import_error"])
        self.assertFalse(run["all_passed"])
        self.assertIn("NotImplementedError", run["shown"][0]["error"])

        for level in (1, 2, 3, 4):
            res = self.client.post(f"/api/sessions/{sid}/submit", json={"code": reference})
            body = res.json()
            self.assertTrue(body["all_passed"], (level, body["breakdown"], body["import_error"]))
            self.assertEqual(body["unlocked"]["completed"], level)
            for t in hidden:  # hidden tests: never ids or names, only counts
                self.assertNotIn(f'"{t["id"]}"', res.text)
                self.assertTrue(t["name"] not in res.text or len(t["name"]) < 12)
            counts = body["breakdown"][str(level)]
            self.assertGreaterEqual(counts["hidden_total"], 8)
            self.assertGreaterEqual(counts["shown_total"], 3)

        self.assertEqual(self.client.post(f"/api/sessions/{sid}/end").status_code, 200)
        review = self.client.get(f"/api/sessions/{sid}/review").json()
        self.assertEqual(review["results"]["timed"]["levels_completed"], 4)
        self.assertTrue(review["hints_html"].strip())
        self.assertTrue(review["analysis_html"].strip())
        self.assertTrue(all(lv["statement_html"].strip() for lv in review["levels"]))

    def test_scratch_example_passes_the_reference_and_fails_the_starter(self):
        for problem in REAL:
            with self.subTest(problem=problem.id), self._session(problem) as sid:
                scratch = self.client.get(f"/api/sessions/{sid}").json()["scratch"]
                self.assertIn("class ExampleTest(unittest.TestCase)", scratch)
                self.assertIn("from solution import *", scratch)

                ok = self.client.post(
                    f"/api/sessions/{sid}/scratch",
                    json={"code": problems.reference_code(problem)},
                ).json()
                self.assertEqual(ok["exit_code"], 0, ok["stdout"] + ok["stderr"])
                self.assertIn("test_example", ok["stdout"])
                self.assertIn("OK", ok["stdout"])

                # On the fresh starter the example stops at the first unimplemented method.
                starter = self.client.post(
                    f"/api/sessions/{sid}/scratch", json={"code": problems.starter_code(problem)}
                ).json()
                self.assertNotEqual(starter["exit_code"], 0)
                self.assertIn("NotImplementedError", starter["stdout"] + starter["stderr"])


if __name__ == "__main__":
    unittest.main()
