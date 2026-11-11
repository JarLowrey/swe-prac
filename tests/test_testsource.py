from __future__ import annotations

import unittest

from support import EnvCase

from swe_prac import problems, testsource


class RenderTests(unittest.TestCase):
    def test_snake_case(self):
        self.assertEqual(testsource.snake_case("FileStore"), "file_store")
        self.assertEqual(testsource.snake_case("InMemoryDB"), "in_memory_db")
        self.assertEqual(testsource.snake_case("TransactionalKV"), "transactional_kv")

    def test_literal_renders_valid_python(self):
        value = ["a", 'say "hi"', (1, "x"), (2,), None, True, 3, {"k": [1]}]
        self.assertEqual(eval(testsource.literal(value)), value)  # noqa: S307

    def test_duplicate_test_names_get_distinct_methods(self):
        tests = [
            {"level": 1, "name": "same name", "steps": [{"call": "f", "args": [1]}]},
            {"level": 1, "name": "Same-Name", "steps": [{"call": "f", "args": [1]}]},
        ]
        source = testsource.tests_file("Thing", tests, 1)
        self.assertIn("def test_same_name(self)", source)
        self.assertIn("def test_same_name_2(self)", source)

    def test_tuples_and_unchecked_steps_round_trip(self):
        tests = [
            {
                "level": 1,
                "name": "tuples",
                "steps": [
                    {"call": "order", "args": [1, {"__tuple__": ["sku", 2]}]},
                    {"call": "total", "args": [2], "expect": 5},
                ],
            }
        ]
        source = testsource.tests_file("Shop", tests, 1)
        self.assertIn('        shop.order(1, ("sku", 2))\n', source)
        self.assertIn("self.assertEqual(shop.total(2), 5)", source)

    def test_assertion_kind_matches_the_expected_type(self):
        cases = [  # a list, not a dict: False and 0 would collide as keys
            (True, "self.assertIs(thing.f(1), True)"),
            (False, "self.assertIs(thing.f(1), False)"),
            (None, "self.assertIsNone(thing.f(1))"),
            (0, "self.assertEqual(thing.f(1), 0)"),
        ]
        for expect, line in cases:
            with self.subTest(expect=expect):
                steps = [{"call": "f", "args": [1], "expect": expect}]
                tests = [{"level": 1, "name": "x", "steps": steps}]
                self.assertIn(line, testsource.tests_file("Thing", tests, 1))

    def test_one_class_per_level_and_a_main_guard(self):
        tests = [
            {"level": 1, "name": "a", "steps": [{"call": "f", "args": [1]}]},
            {"level": 2, "name": "b", "steps": [{"call": "g", "args": [1]}]},
        ]
        source = testsource.tests_file("Thing", tests, 2)
        self.assertIn("class Level1Tests(unittest.TestCase):", source)
        self.assertIn("class Level2Tests(unittest.TestCase):", source)
        self.assertTrue(source.endswith('if __name__ == "__main__":\n    unittest.main()\n'))

    def test_scratch_starter_without_tests_is_just_the_header(self):
        self.assertLessEqual(testsource.scratch_starter("Thing", None).count("\n"), 3)


class FixtureProblemTests(EnvCase):
    def test_tests_file_lists_only_shown_tests_up_to_the_level(self):
        source = problems.shown_tests_source(problems.get("p0_counter"), 2)
        self.assertIn("def test_incr_counts_up(self)", source)
        self.assertIn('counter.incr(1, "a")', source)
        self.assertIn('self.assertIsNone(counter.get(3, "b"))', source)
        self.assertIn("Levels 1-2", source)
        # Hidden tests and later levels never appear.
        self.assertNotIn("SECRET-HIDDEN-NAME", source)
        self.assertNotIn("zz-secret-key", source)
        self.assertNotIn("reset", source)
        self.assertNotIn("total", source)

    def test_level_one_file_says_level_one(self):
        source = problems.shown_tests_source(problems.get("p0_counter"), 1)
        self.assertIn("Shown tests for Level 1 (read-only)", source)

    def test_scratch_starter_has_an_example_case(self):
        scratch = problems.scratch_starter(problems.get("p0_counter"))
        self.assertTrue(scratch.startswith("# Scratch"))
        self.assertIn("from solution import *", scratch)
        self.assertIn("class ExampleTest(unittest.TestCase):", scratch)
        self.assertIn('self.assertEqual(counter.incr(1, "a"), 1)', scratch)
        self.assertIn('self.assertEqual(counter.incr(2, "a"), 2)', scratch)
        self.assertNotIn("SECRET-HIDDEN-NAME", scratch)
        self.assertNotIn("reset", scratch)


if __name__ == "__main__":
    unittest.main()
