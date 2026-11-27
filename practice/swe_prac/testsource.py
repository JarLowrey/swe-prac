"""Render built test data as Python source for the editor.

Two views are generated from a problem's tests.json, so every problem gets them:
  * tests.py, the read-only tab listing the shown tests of the unlocked levels;
  * the example test case that seeds scratch.py.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable

from .runner import decode


def snake_case(name: str) -> str:
    """`InMemoryDB` -> `in_memory_db`."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()


def literal(value) -> str:
    """Python source for a decoded test value (str, int, bool, None, list, tuple, dict)."""
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)  # double quotes, like the statements
    if isinstance(value, tuple):
        inner = ", ".join(literal(v) for v in value)
        return f"({inner},)" if len(value) == 1 else f"({inner})"
    if isinstance(value, list):
        return "[" + ", ".join(literal(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{literal(k)}: {literal(v)}" for k, v in value.items()) + "}"
    return repr(value)


def _call(obj: str, step: dict) -> str:
    return f"{obj}.{step['call']}({', '.join(literal(a) for a in step['args'])})"


def _assertion(call: str, expect) -> str:
    # Mirror the runner: True/False/None must match by identity, everything else by value.
    if expect is None:
        return f"self.assertIsNone({call})"
    if isinstance(expect, bool):
        return f"self.assertIs({call}, {expect!r})"
    return f"self.assertEqual({call}, {literal(expect)})"


def _steps(obj: str, class_name: str, steps: list[dict]) -> list[str]:
    """Body of a test method: a fresh instance, then one assertion (or bare call) per step."""
    lines = [f"        {obj} = {class_name}()"]
    for step in steps:
        call = _call(obj, step)
        lines.append(f"        {_assertion(call, step['expect']) if 'expect' in step else call}")
    return lines


def _function_names(tests: list[dict]) -> list[str]:
    names, seen = [], set()
    for test in tests:
        base = "test_" + (re.sub(r"[^a-z0-9]+", "_", test["name"].lower()).strip("_") or "case")
        name, n = base, 2
        while name in seen:
            name, n = f"{base}_{n}", n + 1
        seen.add(name)
        names.append(name)
    return names


def tests_file(class_name: str, tests: Iterable[dict], max_level: int) -> str:
    """tests.py: a unittest class per level, a method per shown test, each on a fresh instance."""
    tests = [decode(t) for t in tests]
    obj = snake_case(class_name)
    levels = "Level 1" if max_level == 1 else f"Levels 1-{max_level}"
    out = [
        f'"""Shown tests for {levels} (read-only).',
        "",
        f"Run executes exactly these. Every test starts from a fresh {class_name}().",
        "Submit also runs the hidden tests: they aren't listed here and report only how many",
        "pass per level.",
        '"""',
        "",
        "import unittest",
        "",
        "from solution import *  # noqa: F403",
    ]
    names = _function_names(tests)
    current_level = None
    for test, name in zip(tests, names, strict=True):
        if test["level"] != current_level:
            current_level = test["level"]
            out += ["", "", f"class Level{current_level}Tests(unittest.TestCase):"]
        else:
            out.append("")
        out += [f"    def {name}(self) -> None:", f"        {literal(test['name'])}"]
        out += _steps(obj, class_name, test["steps"])
    out += ["", "", 'if __name__ == "__main__":', "    unittest.main()"]
    return "\n".join(out) + "\n"


def scratch_starter(class_name: str, first_test: dict | None) -> str:
    """The scratch.py a session starts with: imports and an example unittest case."""
    out = [
        "# Scratch: run quick experiments against your class.",
        "from solution import *  # noqa: F403",
        "",
    ]
    if first_test is None:
        return "\n".join(out) + "\n"
    out[1:1] = ["import sys", "import unittest", ""]
    out += [
        "",
        "class ExampleTest(unittest.TestCase):",
        "    # The first shown test (see tests.py). Copy it, change the calls and add your own",
        "    # cases. Until you implement the methods it fails with NotImplementedError.",
        "    def test_example(self) -> None:",
        *_steps(snake_case(class_name), class_name, decode(first_test)["steps"]),
        "",
        "",
        'if __name__ == "__main__":',
        "    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout, verbosity=2))",
    ]
    return "\n".join(out) + "\n"
