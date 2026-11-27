"""End-to-end checks over the real problem set in problems/ (not the fixture)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest

from support import TempDirCase

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


class RealProblemRunTests(TempDirCase):
    """The reference passes every test and the starter fails cleanly, run natively here;
    tests/js/ checks the same in the browser's Python."""

    def test_the_reference_passes_every_level_and_the_starter_fails_cleanly(self):
        for problem in REAL:
            with self.subTest(problem=problem.id):
                every = problems.tests(problem, 4, include_hidden=True)
                ref = execution.run_tests(
                    self.tmp_path / problem.id / "ref",
                    problems.reference_code(problem),
                    problem.class_name,
                    every,
                )
                self.assertIsNone(ref.import_error)
                self.assertFalse(ref.timed_out or ref.crashed or ref.stopped)
                self.assertEqual(sorted(ref.results), sorted(t["id"] for t in every))
                failed = [tid for tid, r in ref.results.items() if not r["passed"]]
                self.assertEqual(failed, [])
                for level in (1, 2, 3, 4):
                    at = [t for t in every if t["level"] == level]
                    self.assertGreaterEqual(sum(t["visibility"] == "hidden" for t in at), 8)
                    self.assertGreaterEqual(sum(t["visibility"] == "shown" for t in at), 3)

                # The starter imports cleanly and fails with NotImplementedError, not a crash.
                shown = problems.tests(problem, 1, include_hidden=False)
                starter = execution.run_tests(
                    self.tmp_path / problem.id / "starter",
                    problems.starter_code(problem),
                    problem.class_name,
                    shown,
                )
                self.assertIsNone(starter.import_error)
                first = starter.results[shown[0]["id"]]
                self.assertFalse(first["passed"])
                self.assertIn("NotImplementedError", first["error"])

    def test_every_page_of_the_problem_has_text(self):
        for problem in REAL:
            with self.subTest(problem=problem.id):
                for level in (1, 2, 3, 4):
                    self.assertTrue(problems.statement_html(problem, level).strip())
                for name in ("hints", "analysis"):
                    self.assertTrue(problems.review_html(problem, name).strip())

    def test_scratch_example_passes_the_reference_and_fails_the_starter(self):
        for problem in REAL:
            with self.subTest(problem=problem.id):
                scratch = problems.scratch_starter(problem)
                self.assertIn("class ExampleTest(unittest.TestCase)", scratch)
                self.assertIn("from solution import *", scratch)

                ok = execution.run_scratch(
                    self.tmp_path / problem.id / "ok", problems.reference_code(problem), scratch
                )
                self.assertEqual(ok["exit_code"], 0, ok["stdout"] + ok["stderr"])
                self.assertIn("test_example", ok["stdout"] + ok["stderr"])
                self.assertIn("OK", ok["stdout"] + ok["stderr"])

                # On the fresh starter the example stops at the first unimplemented method.
                starter = execution.run_scratch(
                    self.tmp_path / problem.id / "starter", problems.starter_code(problem), scratch
                )
                self.assertNotEqual(starter["exit_code"], 0)
                self.assertIn("NotImplementedError", starter["stdout"] + starter["stderr"])


if __name__ == "__main__":
    unittest.main()
