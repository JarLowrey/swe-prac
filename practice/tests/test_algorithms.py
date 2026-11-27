"""The algorithms loader (fixture set) and checks over the real problem set in algorithms/."""

from __future__ import annotations

import json
import shutil
import unittest

from support import EnvCase

from swe_prac import algorithms, config, pages

REAL = algorithms.list_problems()  # loaded before any test patches config.ALGO_DIR


class LoaderTests(EnvCase):
    def _rewrite_meta(self, problem_id, **changes):
        path = config.ALGO_DIR / problem_id / "problem.json"
        meta = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps({**meta, **changes}), encoding="utf-8")

    def test_problems_load_in_order_and_unfinished_ones_are_skipped(self):
        self.assertEqual(
            [p.id for p in algorithms.list_problems()], ["x01_pair_sum", "x02_reverse_list"]
        )
        draft = config.ALGO_DIR / "x03_draft"  # problem.json only, as a skeleton starts out
        draft.mkdir()
        shutil.copy(config.ALGO_DIR / "x01_pair_sum" / "problem.json", draft / "problem.json")
        self.assertEqual(len(algorithms.list_problems()), 2)
        for bad in ("x03_draft", "../x01_pair_sum", "x01_pair_sum/..", "nope"):
            with self.assertRaises(algorithms.ProblemNotFound, msg=bad):
                algorithms.get(bad)

    def test_public_fields_and_time_limits(self):
        pair = algorithms.get("x01_pair_sum")
        self.assertEqual(
            pair.public(),
            {
                "id": "x01_pair_sum",
                "number": 1,
                "title": "Pair Sum (test fixture)",
                "difficulty": "Easy",
                "patterns": ["Hashing"],
                "minutes": 20,
                "method": "pairSum",
            },
        )
        self.assertEqual(pair.time_limit, 20 * 60)
        self.assertEqual(algorithms.get("x02_reverse_list").time_limit, 30 * 60)
        self._rewrite_meta("x01_pair_sum", minutes=25)
        self.assertEqual(algorithms.get("x01_pair_sum").time_limit, 25 * 60)
        self._rewrite_meta("x01_pair_sum", difficulty="Impossible")
        with self.assertRaises(ValueError):
            algorithms.get("x01_pair_sum")

    def test_tests_and_examples(self):
        pair = algorithms.get("x01_pair_sum")
        shown = algorithms.tests(pair, include_hidden=False)
        self.assertEqual([t["visibility"] for t in shown], ["shown", "shown"])
        everything = algorithms.tests(pair, include_hidden=True)
        self.assertEqual(len(everything), 5)
        self.assertEqual(
            everything[2]["steps"],
            [{"call": "pairSum", "args": [[-3, 4, 3, 90], 0], "expect": [0, 2]}],
        )
        self.assertEqual(
            algorithms.shown_cases(pair)[0],
            {"id": "s1", "name": "Example 1", "args": [[2, 7, 11, 15], 9], "expect": [0, 1]},
        )
        self.assertEqual(algorithms.param_names(pair), ["nums", "target"])

    def test_starter_code_and_scratch(self):
        pair = algorithms.get("x01_pair_sum")
        self.assertEqual(
            algorithms.starter_code(pair),
            "class Solution:\n"
            "    def pairSum(self, nums: list[int], target: int) -> list[int]:\n"
            "        pass\n",
        )
        rev = algorithms.get("x02_reverse_list")
        starter = algorithms.starter_code(rev)
        self.assertTrue(starter.startswith("from typing import Optional\n"))
        self.assertIn("class ListNode:", starter)
        compile(starter, "starter", "exec")
        scratch = algorithms.scratch_starter(rev)
        self.assertIn("head = make_list([1, 2, 3])", scratch)
        self.assertIn("print(list_values(result))", scratch)
        self.assertIn("# expected: [3, 2, 1]", scratch)

    def test_runner_options(self):
        self.assertEqual(
            algorithms.get("x02_reverse_list").runner_options(),
            {
                "normalize": True,
                "deep_recursion": True,
                "compare": "exact",
                "adapters": {"args": ["listnode"], "result": "listnode"},
            },
        )
        self._rewrite_meta("x01_pair_sum", compare="validator")
        checker = "def check(args, expect, actual):\n    return True\n"
        checker_js = "function check(args, expect, actual) {\n  return true;\n}\n"
        (config.ALGO_DIR / "x01_pair_sum" / "checker.py").write_text(checker, encoding="utf-8")
        (config.ALGO_DIR / "x01_pair_sum" / "checker.js").write_text(checker_js, encoding="utf-8")
        opts = algorithms.get("x01_pair_sum").runner_options()
        self.assertEqual((opts["validator"], opts["validator_js"]), (checker, checker_js))

    def test_foundation_links_resolve_and_unknown_ones_are_dropped(self):
        links = algorithms.foundation_links(algorithms.get("x01_pair_sum"))
        self.assertEqual(
            [(f["title"], f["page_title"], f["href"]) for f in links],
            [
                ("Hashing", "Basics", "#/algo/learn/basics/hashing"),
                ("Basics", "Basics", "#/algo/learn/basics"),
            ],
        )
        folder = algorithms.foundations_dir()
        self.assertEqual(pages.links(folder, "#/algo/learn", ["basics/nope", "nope"]), [])


class RealCatalogueTests(unittest.TestCase):
    """Every built problem in algorithms/ (a problem without tests.json isn't listed)."""

    def test_problems_are_complete(self):
        self.assertGreaterEqual(len(REAL), 15)
        numbers = [p.number for p in REAL]
        self.assertEqual(len(numbers), len(set(numbers)))
        for p in REAL:
            with self.subTest(problem=p.id):
                self.assertEqual(p.path.name, p.id)
                self.assertTrue(p.patterns)
                shown = algorithms.tests(p, include_hidden=False)
                everything = algorithms.tests(p, include_hidden=True)
                self.assertTrue(shown)
                self.assertGreater(len(everything), len(shown))  # some hidden tests
                self.assertTrue(algorithms.foundation_links(p))  # links into the foundations
                compile(algorithms.starter_code(p), p.id, "exec")
                compile(algorithms.scratch_starter(p), p.id, "exec")


if __name__ == "__main__":
    unittest.main()
