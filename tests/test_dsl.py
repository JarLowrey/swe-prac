from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import dsl  # noqa: E402


class DslTests(unittest.TestCase):
    def test_parse_blocks_and_steps(self):
        src = """
# leading comment
=== L1 shown: basics
add(1, "a;b", 2) -> True   # semicolon inside a string
add(2, "x") ; get(3, "x") -> None
get(4, "# not a comment") -> ?

=== L3 hidden: random @gen(seed=7, n=50)
"""
        blocks = dsl.parse_tests(src)
        self.assertEqual(
            [(b.level, b.visibility, b.name) for b in blocks],
            [(1, "shown", "basics"), (3, "hidden", "random")],
        )
        steps = blocks[0].steps
        self.assertEqual(steps[0].args, [1, "a;b", 2])
        self.assertIs(steps[0].expect, True)
        self.assertIs(steps[1].expect, dsl.UNCHECKED)
        self.assertIsNone(steps[2].expect)
        self.assertEqual(steps[3].args, [4, "# not a comment"])
        self.assertIs(steps[3].expect, dsl.GOLDEN)
        self.assertEqual(blocks[1].gen, {"seed": 7, "n": 50})

    def test_tuples_and_arrow_in_string(self):
        step = dsl.parse_step('place(5, [("A", 2), ("B", 1)]) -> "a->b"', 1)
        self.assertEqual(step.args, [5, [("A", 2), ("B", 1)]])
        self.assertEqual(step.expect, "a->b")

    def test_errors(self):
        bad_sources = [
            "=== L5 shown: no such level",
            "=== L1 shown: x\nadd(1, x) -> 1",  # non-literal argument
            "add(1) -> 1",  # step before header
            "=== L1 shown: x\nadd(1, k=2)",  # keyword args
        ]
        for bad in bad_sources:
            with self.subTest(bad=bad), self.assertRaises(dsl.DSLError):
                dsl.parse_tests(bad)


if __name__ == "__main__":
    unittest.main()
