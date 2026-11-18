from __future__ import annotations

import threading
import time
import unittest
from unittest import mock

from support import TempDirCase

from swe_prac import config, execution, runner
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


def _calls(*cases):
    """One-step tests calling f: (args, expect) or (args, expect, limit_ms)."""
    out = []
    for i, (args, expect, *limit) in enumerate(cases):
        test = {
            "id": f"T{i}",
            "name": f"t{i}",
            "visibility": "shown",
            "steps": [{"call": "f", "args": args, "expect": expect}],
        }
        if limit:
            test["limit_ms"] = limit[0]
        out.append(test)
    return out


REVERSE = """class Solution:
    def f(self, head):
        prev = None
        while head:
            nxt = head.next
            head.next = prev
            prev, head = head, nxt
        return prev
"""

INVERT = """class Solution:
    def f(self, root):
        if root:
            root.left, root.right = self.f(root.right), self.f(root.left)
        return root
"""

CLONE = """class Node:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []


class Solution:
    def f(self, node):
        copies = {}

        def visit(n):
            if n not in copies:
                copies[n] = Node(n.val)
                copies[n].neighbors = [visit(m) for m in n.neighbors]
            return copies[n]

        return visit(node) if node else None
"""

IDENTITY = "class Solution:\n    def f(self, x):\n        return x\n"


class AlgorithmOptionsTests(TempDirCase):
    """The runner options of the algorithms track: adapters, compare modes, time limits."""

    def run_code(self, code, tests, **options):
        return execution.run_tests(self.tmp_path, code, "Solution", tests, options)

    def test_linked_lists_in_and_out(self):
        run = self.run_code(
            REVERSE,
            _calls(([[1, 2, 3]], [3, 2, 1]), ([[]], [])),
            adapters={"args": ["listnode"], "result": "listnode"},
        )
        self.assertEqual([r["passed"] for r in run.results.values()], [True, True], run.results)

    def test_in_place_methods_are_checked_through_their_argument(self):
        code = "class Solution:\n    def f(self, head):\n        head.val = 9\n"
        run = self.run_code(
            code, _calls(([[1, 2]], [9, 2])), adapters={"args": ["listnode"], "check": "arg0"}
        )
        self.assertTrue(run.results["T0"]["passed"], run.results["T0"])

    def test_a_returned_list_with_a_cycle_is_reported(self):
        code = (
            "class Solution:\n    def f(self, head):\n"
            "        head.next.next = head\n        return head\n"
        )
        run = self.run_code(
            code, _calls(([[1, 2]], [1, 2])), adapters={"args": ["listnode"], "result": "listnode"}
        )
        result = run.results["T0"]
        self.assertFalse(result["passed"])
        self.assertIn("cycle", result["error"])

    def test_trees_round_trip_in_level_order(self):
        run = self.run_code(
            INVERT,
            _calls(([[4, 2, 7, 1, 3]], [4, 7, 2, None, None, 3, 1])),
            adapters={"args": ["tree"], "result": "tree"},
        )
        self.assertTrue(run.results["T0"]["passed"], run.results["T0"])

    def test_a_graph_clone_must_not_reuse_the_original_nodes(self):
        tests = _calls(([[[2], [1]]], [[2], [1]]))
        adapters = {"args": ["graph"], "result": "graph"}
        self.assertTrue(self.run_code(CLONE, tests, adapters=adapters).results["T0"]["passed"])
        same = self.run_code(IDENTITY, tests, adapters=adapters).results["T0"]
        self.assertFalse(same["passed"])
        self.assertIn("reuses nodes", same["error"])

    def test_compare_modes(self):
        def passed(code, case, **options):
            return self.run_code(code, _calls(case), **options).results["T0"]

        self.assertTrue(passed(IDENTITY, ([[3, 1, 2]], [1, 2, 3]), compare="unordered")["passed"])
        self.assertFalse(passed(IDENTITY, ([[3, 1, 2]], [1, 2, 3]), compare="exact")["passed"])
        nested = ([[[2, 1], [3]]], [[3], [1, 2]])
        self.assertTrue(passed(IDENTITY, nested, compare="unordered_nested")["passed"])
        self.assertFalse(passed(IDENTITY, nested, compare="unordered")["passed"])
        validator = (
            "def check(args, expect, actual):\n    return actual == args[0] or 'not the input'\n"
        )
        wrong = passed(
            "class Solution:\n    def f(self, x):\n        return [0]\n",
            ([[1]], [1]),
            compare="validator",
            validator=validator,
        )
        self.assertFalse(wrong["passed"])
        self.assertEqual(wrong["error"], "not the input")
        self.assertTrue(
            passed(IDENTITY, ([[1]], [9]), compare="validator", validator=validator)["passed"]
        )

    def test_tuples_in_results_match_lists(self):
        code = "class Solution:\n    def f(self):\n        return (1, (2, 3))\n"
        self.assertTrue(
            self.run_code(code, _calls(([], [1, [2, 3]])), normalize=True).results["T0"]["passed"]
        )

    def test_deep_recursion(self):
        code = (
            "class Solution:\n    def f(self, n):\n"
            "        return 0 if n == 0 else 1 + self.f(n - 1)\n"
        )
        result = self.run_code(code, _calls(([20_000], 20_000)), deep_recursion=True).results["T0"]
        self.assertTrue(result["passed"], result)

    def test_a_slow_answer_fails_and_a_stuck_call_stops_the_run(self):
        code = (
            "import time\n\n\nclass Solution:\n    def f(self, seconds):\n"
            "        time.sleep(seconds)\n        return seconds\n"
        )
        # Right but over its 200 ms limit; then stuck past 100 ms x 1.5; then never run.
        run = self.run_code(code, _calls(([0.22], 0.22, 200), ([5], 5, 100), ([0], 0)))
        self.assertFalse(run.results["T0"]["passed"])
        self.assertIn("The answer was right", run.results["T0"]["error"])
        self.assertTrue(run.results["T1"]["error"].startswith("Too slow: stopped after 150 ms"))
        self.assertNotIn("T2", run.results)
        self.assertTrue(run.stopped.startswith("Too slow"))


class CallTimingTests(unittest.TestCase):
    def test_timing_counts_the_call_but_not_starting_its_thread(self):
        real_start = threading.Thread.start

        def slow_start(thread):
            time.sleep(0.2)  # what a busy machine can do to a thread with a 64 MB stack
            real_start(thread)

        timing: dict = {}
        with mock.patch.object(threading.Thread, "start", slow_start):
            self.assertEqual(runner.call(lambda x: x + 1, [1], deep=True, timing=timing), 2)
        self.assertLess(timing["ms"], 100)
        runner.call(time.sleep, [0.05], deep=True, timing=timing)
        self.assertGreaterEqual(timing["ms"], 45)
        runner.call(time.sleep, [0.05], deep=False, timing=timing)  # no thread
        self.assertGreaterEqual(timing["ms"], 45)


class LintFormatTests(unittest.TestCase):
    def test_lint_and_format(self):
        lint = execution.lint("import os\nx=1\n")
        self.assertIn("F401", {i["code"] for i in lint["issues"]})
        formatted = execution.format_code("x=[1,2 ,3]\n")
        self.assertEqual(formatted["code"], "x = [1, 2, 3]\n")
        self.assertTrue(execution.format_code("def (:\n")["error"])

    def test_the_algorithms_config_allows_camel_case_method_names(self):
        code = "class Solution:\n    def twoSum(self, numList):\n        return numList\n"
        coding = {i["code"] for i in execution.lint(code)["issues"]}
        self.assertTrue({"N802", "N803"} <= coding, coding)
        algo = {i["code"] for i in execution.lint(code, config.ALGO_RUFF_CONFIG)["issues"]}
        self.assertFalse(algo & {"N802", "N803"}, algo)


if __name__ == "__main__":
    unittest.main()
