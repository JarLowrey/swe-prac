from __future__ import annotations

import unittest

from support import TempDirCase

from swe_prac import config, execution
from swe_prac.runner import decode, matches


def _tests(*steps_lists):
    return [
        {"id": f"T{i}", "level": 1, "visibility": "shown", "name": f"t{i}", "steps": steps}
        for i, steps in enumerate(steps_lists)
    ]


class MatcherTests(unittest.TestCase):
    def test_matches_is_type_strict(self):
        self.assertTrue(matches(True, True))
        self.assertFalse(matches(True, 1))
        self.assertFalse(matches(1, True))
        self.assertTrue(matches(None, None))
        self.assertFalse(matches(None, 0))
        self.assertFalse(matches(0, None))
        self.assertTrue(matches(10, 10.0))
        self.assertFalse(matches("1", 1))
        self.assertFalse(matches(False, None))

    def test_decode_tuples(self):
        self.assertEqual(decode([{"__tuple__": ["A", 2]}, {"x": 1}]), [("A", 2), {"x": 1}])


class RunnerTests(TempDirCase):
    def test_pass_fail_and_stops_at_first_failure(self):
        code = "class C:\n    def f(self, ts, x):\n        print('saw', x)\n        return x * 2\n"
        tests = _tests(
            [{"call": "f", "args": [1, 2], "expect": 4}],
            [
                {"call": "f", "args": [1, 2], "expect": 5},
                {"call": "f", "args": [2, 3], "expect": 6},
            ],
        )
        run = execution.run_tests(self.tmp_path, code, "C", tests)
        self.assertIsNone(run.import_error)
        self.assertIs(run.results["T0"]["passed"], True)
        self.assertIn("saw 2", run.results["T0"]["stdout"])
        bad = run.results["T1"]
        self.assertIs(bad["passed"], False)
        self.assertEqual(bad["failed_step"], 0)
        self.assertEqual(len(bad["steps"]), 1)  # second step never ran
        self.assertEqual(bad["steps"][0]["expect"], "5")
        self.assertEqual(bad["steps"][0]["actual"], "4")

    def test_exception_traceback_shows_only_user_frames(self):
        code = "class C:\n    def f(self, ts):\n        return {}['missing']\n"
        run = execution.run_tests(
            self.tmp_path, code, "C", _tests([{"call": "f", "args": [1], "expect": 1}])
        )
        result = run.results["T0"]
        self.assertFalse(result["passed"])
        self.assertIn("KeyError", result["error"])
        self.assertIn('File "solution.py", line 3, in f', result["error"])
        self.assertNotIn("runner.py", result["error"])
        self.assertNotIn(str(self.tmp_path), result["error"])  # no absolute session paths

    def test_unchecked_steps_and_missing_method(self):
        code = "class C:\n    def f(self, ts):\n        return 'anything'\n"
        tests = _tests([{"call": "f", "args": [1]}, {"call": "g", "args": [2], "expect": 1}])
        result = execution.run_tests(self.tmp_path, code, "C", tests).results["T0"]
        self.assertIs(result["steps"][0]["ok"], True)
        self.assertIs(result["steps"][0]["checked"], False)
        self.assertIn("`g` is not defined", result["error"])

    def test_syntax_error_and_missing_class(self):
        run = execution.run_tests(self.tmp_path, "class C:\n  def f(:\n", "C", _tests([]))
        self.assertIn("SyntaxError", run.import_error)
        run = execution.run_tests(self.tmp_path, "x = 1\n", "C", _tests([]))
        self.assertIn("class named `C`", run.import_error)

    def test_tuple_args_reach_user_code(self):
        code = (
            "class C:\n"
            "    def f(self, ts, lines):\n"
            "        return all(type(x) is tuple for x in lines)\n"
        )
        tests = _tests([{"call": "f", "args": [1, [{"__tuple__": ["A", 1]}]], "expect": True}])
        self.assertTrue(
            execution.run_tests(self.tmp_path, code, "C", tests).results["T0"]["passed"]
        )

    def test_infinite_loop_times_out_with_partial_results(self):
        self.patch(config, "RUN_TIMEOUT_SECONDS", 3)
        code = (
            "class C:\n    def ok(self, ts):\n        return 1\n"
            "    def spin(self, ts):\n        while True:\n            pass\n"
        )
        tests = _tests(
            [{"call": "ok", "args": [1], "expect": 1}],
            [{"call": "spin", "args": [1], "expect": 1}],
            [{"call": "ok", "args": [1], "expect": 1}],
        )
        run = execution.run_tests(self.tmp_path, code, "C", tests)
        self.assertTrue(run.timed_out)
        self.assertTrue(run.results["T0"]["passed"])
        self.assertFalse(run.results["T1"]["passed"])
        self.assertIn("Timed out", run.results["T1"]["error"])
        self.assertNotIn("T2", run.results)  # never ran

    def test_scratch_imports_solution(self):
        scratch = (
            "import sys\nimport unittest\n\nfrom solution import *\n\n\n"
            "class ScratchTest(unittest.TestCase):\n"
            "    def test_solution_is_importable(self):\n"
            "        print('é')  # non-ASCII output must not crash on Windows\n"
            "        self.assertEqual(C.X + 1, 42)\n\n\n"
            "unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout))\n"
        )
        out = execution.run_scratch(self.tmp_path, "class C:\n    X = 41\n", scratch)
        self.assertEqual(out["exit_code"], 0, out["stdout"] + out["stderr"])
        self.assertIn("é", out["stdout"])
        self.assertIn("OK", out["stdout"])


class LintFormatTests(unittest.TestCase):
    def test_lint_and_format(self):
        lint = execution.lint("import os\nx=1\n")
        self.assertIn("F401", {i["code"] for i in lint["issues"]})
        formatted = execution.format_code("x=[1,2 ,3]\n")
        self.assertEqual(formatted["code"], "x = [1, 2, 3]\n")
        self.assertTrue(execution.format_code("def (:\n")["error"])


if __name__ == "__main__":
    unittest.main()
