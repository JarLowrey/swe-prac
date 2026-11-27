"""The Java and C++ versions generated from each problem's Python signatures (swe_prac.langs).

The JavaScript tests (tests/js/java.test.mjs, cpp.test.mjs) compile and run what this writes;
these check the types and the text."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from support import EnvCase

from swe_prac import algorithms, config, langs, problems
from swe_prac.langs import LangError, parse_type


class ParseTypeTests(unittest.TestCase):
    def test_scalars_lists_and_tuples(self):
        self.assertEqual(str(parse_type("int")), "int")
        self.assertEqual(str(parse_type("list[list[str]]")), "list[list[str]]")
        self.assertEqual(str(parse_type("tuple[str, int]")), "tuple[str, int]")
        self.assertEqual(str(parse_type("List[int]")), "list[int]")
        self.assertEqual(str(parse_type("Tuple[int, int, int]")), "tuple[int, int, int]")

    def test_none_unions_are_optional_except_for_nodes(self):
        self.assertEqual(parse_type("int | None").kind, "optional")
        self.assertEqual(parse_type("None | str").kind, "optional")
        self.assertEqual(parse_type("Optional[int]").kind, "optional")
        # A node is nullable already.
        self.assertEqual(parse_type("TreeNode | None").kind, "treenode")
        self.assertEqual(parse_type("Optional[ListNode]").kind, "listnode")
        self.assertEqual(parse_type("list[Node | None]").args[0].kind, "node")

    def test_types_the_other_languages_cant_express_are_refused(self):
        for text in ("dict[str, int]", "int | str", "set[int]", "tuple[int]", "list[", "Any"):
            with self.subTest(text=text), self.assertRaises(LangError):
                parse_type(text)


def coding_problem(stubs: dict, class_name: str = "Ledger"):
    levels = [{"level": int(k)} for k in stubs if k.isdigit()]
    return SimpleNamespace(id="p9_ledger", class_name=class_name, levels=levels)


def stub(signature: str) -> str:
    return f"    {signature}\n        raise NotImplementedError\n"


def step(call: str, args: list, expect=None) -> dict:
    return {"call": call, "args": args, "expect": expect}


def case(*steps, level: int = 1, visibility: str = "shown", name: str = "basic") -> dict:
    return {"name": name, "level": level, "visibility": visibility, "steps": list(steps)}


class SpecTests(unittest.TestCase):
    STUBS = {
        "1": "    def add_entry(self, timestamp: int, account: str, amount: int) -> bool:\n"
        '        """Add an entry; False if the account is closed."""\n'
        "        raise NotImplementedError\n",
        "2": stub("def balance(self, account: str) -> int | None:"),
    }

    def spec(self, tests: list[dict], meta: dict | None = None, stubs: dict | None = None):
        stubs = stubs or self.STUBS
        return langs.coding_spec(coding_problem(stubs), stubs, tests, meta or {})

    def test_names_are_camel_case_and_keywords_get_an_underscore(self):
        stubs = {"1": stub("def delete(self, key: str) -> bool:")}
        spec = self.spec([case(step("delete", ["a"], True))], stubs=stubs)
        java, cpp = langs.JavaGen(spec), langs.CppGen(spec)
        self.assertEqual(java.name("add_entry"), "addEntry")
        self.assertEqual(java.name("delete"), "delete")  # not a keyword in Java
        self.assertEqual(cpp.name("delete"), "delete_")
        self.assertEqual(java.name("new"), "new_")

    def test_an_int_is_64_bits_only_where_a_test_needs_it(self):
        spec = self.spec([case(step("add_entry", [1, "a", 2**40], True))])
        java, cpp = langs.JavaGen(spec), langs.CppGen(spec)
        (add, balance) = spec.methods
        self.assertEqual(
            java.signature(add),
            "public boolean addEntry(int timestamp, String account, long amount)",
        )
        self.assertEqual(
            cpp.signature(add), "bool addEntry(int timestamp, string account, long long amount)"
        )
        self.assertEqual(java.signature(balance), "public Integer balance(String account)")
        self.assertEqual(cpp.signature(balance), "optional<int> balance(string account)")

    def test_a_call_no_stub_has_is_an_error(self):
        with self.assertRaisesRegex(LangError, "a test calls close"):
            self.spec([case(step("close", ["a"]))])

    def test_a_tuple_needs_a_java_record_name(self):
        stubs = {"1": stub("def lines(self) -> list[tuple[str, int]]:")}
        tests = [case(step("lines", [], [{"__tuple__": ["a", 1]}]))]
        with self.assertRaisesRegex(LangError, "records"):
            self.spec(tests, stubs=stubs)
        with self.assertRaisesRegex(LangError, "needs 2 field names"):
            self.spec(tests, {"records": {"tuple[str, int]": "Line(sku)"}}, stubs)
        spec = self.spec(tests, {"records": {"tuple[str, int]": "Line(sku, qty)"}}, stubs)
        java, cpp = langs.JavaGen(spec), langs.CppGen(spec)
        self.assertEqual(java.signature(spec.methods[0]), "public List<Line> lines()")
        self.assertIn("record Line(String sku, int qty) {}", java.starter_code())
        self.assertIn("SweTypes.java", java.support_files())
        self.assertEqual(cpp.signature(spec.methods[0]), "vector<pair<string, int>> lines()")

    def test_docstrings_use_each_languages_words(self):
        spec = self.spec([case(step("add_entry", [1, "a", 2], True))])
        self.assertIn(
            "/** Add an entry; false if the account is closed. */",
            langs.JavaGen(spec).level_stubs(1),
        )
        self.assertIn(
            "// Add an entry; false if the account is closed.", langs.CppGen(spec).level_stubs(1)
        )

    def test_the_starter_has_level_1_and_each_harness_only_the_unlocked_levels(self):
        spec = self.spec([case(step("add_entry", [1, "a", 2], True))])
        for gen in langs.generators(spec).values():
            with self.subTest(lang=gen.lang):
                self.assertIn("addEntry(", gen.starter_code())
                self.assertNotIn("balance(", gen.starter_code())
                self.assertNotIn("balance", gen.harness(1))
                self.assertIn('"balance"', gen.harness(2))
                self.assertIn("balance(", gen.level_stubs(2))

    def test_java_return_overrides_the_usual_return_type(self):
        problem = SimpleNamespace(
            id="x9_merge",
            signature="def merge(self, intervals: list[list[int]]) -> list[list[int]]:",
            adapters=None,
        )
        cases = [{"args": [[[1, 3], [2, 4]]], "expect": [[1, 4]]}]
        spec = langs.algo_spec(problem, cases, {})
        self.assertEqual(
            langs.JavaGen(spec).signature(spec.methods[0]),
            "public List<List<Integer>> merge(int[][] intervals)",
        )
        spec = langs.algo_spec(problem, cases, {"java_return": "int[][]"})
        self.assertEqual(
            langs.JavaGen(spec).signature(spec.methods[0]),
            "public int[][] merge(int[][] intervals)",
        )
        self.assertEqual(
            langs.CppGen(spec).signature(spec.methods[0]),
            "vector<vector<int>> merge(vector<vector<int>>& intervals)",
        )

    def test_an_adapter_that_doesnt_match_the_signature_is_an_error(self):
        problem = SimpleNamespace(
            id="x9_rev",
            signature="def rev(self, head: list[int]) -> list[int]:",
            adapters={"args": ["listnode"], "result": "listnode"},
        )
        with self.assertRaisesRegex(LangError, "adapter 'listnode'"):
            langs.algo_spec(problem, [{"args": [[1]], "expect": [1]}], {})


class FixtureTests(EnvCase):
    """What the build writes for the fixture problems."""

    def coding(self) -> dict:
        problem = problems.get("p0_counter")
        shown = {lv: problems.tests(problem, lv, include_hidden=False) for lv in config.LEVELS}
        return langs.coding_bundle(langs.for_coding(problem), shown)

    def test_a_coding_problem_has_each_languages_files_stubs_and_tests_view(self):
        bundle = self.coding()
        self.assertEqual(sorted(bundle), ["cpp", "java"])
        java, cpp = bundle["java"], bundle["cpp"]
        self.assertEqual((java["file"], cpp["file"]), ("Counter.java", "solution.cpp"))
        self.assertEqual(sorted(java["stubs"]), ["1", "2", "3", "4"])
        self.assertIn("public Integer get(int timestamp, String key)", java["stubs"]["2"])
        self.assertIn("optional<int> get(int timestamp, string key)", cpp["stubs"]["2"])
        self.assertIn("class Counter {", java["starter_code"])
        self.assertIn("Counter counter = new Counter();", java["scratch_starter"])
        self.assertIn(
            'cout << show(counter.incr(1, "a")) << endl;  // expected: 1', cpp["scratch_starter"]
        )
        # The tests view lists the shown tests of every unlocked level.
        self.assertIn("class Level1Tests", java["tests_source"]["1"])
        self.assertNotIn("class Level2Tests", java["tests_source"]["1"])
        self.assertIn('assertNull(counter.get(3, "b"));', java["tests_source"]["2"])
        self.assertIn('EXPECT_EQ(counter.get(3, "b"), nullopt);', cpp["tests_source"]["2"])
        self.assertIn("TEST(Level4, Total)", cpp["tests_source"]["4"])
        self.assertEqual(
            java["names"], {"incr": "incr", "get": "get", "reset": "reset", "total": "total"}
        )

    def test_the_hidden_tests_stay_out_of_the_tests_view(self):
        problem = problems.get("p0_counter")
        hidden = [
            t
            for t in problems.tests(problem, 4, include_hidden=True)
            if t["visibility"] == "hidden"
        ]
        self.assertTrue(hidden)
        text = str(self.coding())
        for test in hidden:
            self.assertNotIn(langs.pascal(test["name"]), text)

    def test_an_algorithm_problem_has_its_signature_starter_and_scratch(self):
        pair = langs.algo_bundle(langs.for_algo(algorithms.get("x01_pair_sum")))
        self.assertEqual(pair["java"]["signature"], "public int[] pairSum(int[] nums, int target)")
        self.assertEqual(
            pair["cpp"]["signature"], "vector<int> pairSum(vector<int>& nums, int target)"
        )
        self.assertIn("int[] nums = new int[] {2, 7, 11, 15};", pair["java"]["scratch_starter"])
        self.assertIn("vector<int> nums = {2, 7, 11, 15};", pair["cpp"]["scratch_starter"])

        rev = langs.algo_bundle(langs.for_algo(algorithms.get("x02_reverse_list")))
        self.assertEqual(rev["java"]["signature"], "public ListNode reverseList(ListNode head)")
        self.assertEqual(rev["cpp"]["signature"], "ListNode* reverseList(ListNode* head)")
        for lang in ("java", "cpp"):
            self.assertIn("Definition for a singly-linked list node", rev[lang]["starter_code"])
        self.assertIn("Helpers.makeList(1, 2, 3)", rev["java"]["scratch_starter"])
        self.assertIn("makeList({1, 2, 3})", rev["cpp"]["scratch_starter"])

    def test_the_harness_files_carry_the_node_types_the_problem_uses(self):
        pair = langs.harness_files(langs.for_algo(algorithms.get("x01_pair_sum")))
        rev = langs.harness_files(langs.for_algo(algorithms.get("x02_reverse_list")))
        self.assertNotIn("ListNode.java", pair["java"]["files"])
        self.assertIn("ListNode.java", rev["java"]["files"])
        self.assertIn("#define SWE_LISTNODE 1", rev["cpp"]["files"]["swe_nodes.hpp"])
        self.assertNotIn("SWE_LISTNODE", pair["cpp"]["files"]["swe_nodes.hpp"])
        self.assertIsInstance(pair["java"]["harness"], str)  # one harness: no levels
        coding = langs.harness_files(langs.for_coding(problems.get("p0_counter")))
        self.assertEqual(sorted(coding["cpp"]["harness"]), ["1", "2", "3", "4"])


class RealCatalogueTests(unittest.TestCase):
    """Every real problem has a Java and a C++ version (the JS tests compile and run them)."""

    def test_every_problem_generates(self):
        coding = problems.list_problems()
        algo = algorithms.list_problems()
        self.assertTrue(coding and algo)
        for problem in coding:
            with self.subTest(problem=problem.id):
                spec = langs.for_coding(problem)
                harness = langs.harness_files(spec)
                for lang in langs.LANGUAGES:
                    self.assertEqual(sorted(harness[lang]["harness"]), ["1", "2", "3", "4"])
        for problem in algo:
            with self.subTest(problem=problem.id):
                bundle = langs.algo_bundle(langs.for_algo(problem))
                for lang in langs.LANGUAGES:
                    self.assertIn("class Solution", bundle[lang]["starter_code"])


if __name__ == "__main__":
    unittest.main()
