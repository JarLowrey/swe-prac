"""Algorithm problems from algorithms/<id>/ and the algorithms foundations pages.

A problem folder holds problem.json (metadata), statement.md, hints.md, explanation.md,
solution.py (the reference solution), cases.py (the test inputs), checker.py (only when several
answers are right) and tests.json, which tools/build_algo.py generates from cases.py and the
reference. algorithms/README.md documents the format.

A session shows the shown tests only (the examples); Submit runs the hidden ones too and reports
counts for them.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import config, pages
from .problems import render_markdown


class ProblemNotFound(KeyError):
    pass


# Helper classes a solution needs for its arguments, put at the top of the starter code (the
# runner builds the inputs with the solution's own classes, so they can be edited freely).
NODE_CLASSES = {
    "listnode": """class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
""",
    "tree": """class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
""",
    "graph": """class Node:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []
""",
}
NODE_CLASSES["listnodes"] = NODE_CLASSES["listnode"]


@dataclass(frozen=True)
class Problem:
    id: str
    number: int
    title: str
    difficulty: str
    patterns: tuple[str, ...]
    signature: str  # "def twoSum(self, nums: List[int], target: int) -> List[int]:"
    path: Path
    adapters: dict = field(default_factory=dict)
    compare: str = "exact"
    foundations: tuple[str, ...] = ()  # "page/section" references into algorithms/foundations
    minutes: int = 30

    @property
    def method(self) -> str:
        return re.match(r"\s*def\s+(\w+)\s*\(", self.signature).group(1)

    @property
    def time_limit(self) -> int:
        return self.minutes * 60

    def public(self) -> dict:
        """Safe to show any time, including during a session."""
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "difficulty": self.difficulty,
            "patterns": list(self.patterns),
            "minutes": self.minutes,
            "method": self.method,
        }

    def runner_options(self) -> dict:
        """How the runner adapts arguments and compares results (see runner.py)."""
        opts = {"normalize": True, "deep_recursion": True, "compare": self.compare}
        if self.adapters:
            opts["adapters"] = self.adapters
        if self.compare == "validator":
            opts["validator"] = (self.path / "checker.py").read_text(encoding="utf-8")
        return opts


REQUIRED = ("problem.json", "statement.md", "hints.md", "explanation.md", "solution.py")


def _is_ready(path: Path) -> bool:
    return all((path / name).exists() for name in (*REQUIRED, "tests.json"))


def _load(path: Path) -> Problem:
    data = json.loads((path / "problem.json").read_text(encoding="utf-8"))
    difficulty = data["difficulty"]
    if difficulty not in config.ALGO_MINUTES:
        raise ValueError(f"{path.name}: difficulty must be one of {config.ALGO_DIFFICULTIES}")
    return Problem(
        id=data["id"],
        number=data["number"],
        title=data["title"],
        difficulty=difficulty,
        patterns=tuple(data.get("patterns", ())),
        signature=data["signature"],
        path=path,
        adapters=data.get("adapters") or {},
        compare=data.get("compare", "exact"),
        foundations=tuple(data.get("foundations", ())),
        minutes=data.get("minutes", config.ALGO_MINUTES[difficulty]),
    )


def list_problems() -> list[Problem]:
    if not config.ALGO_DIR.exists():
        return []
    found = [_load(p) for p in config.ALGO_DIR.iterdir() if p.is_dir() and _is_ready(p)]
    return sorted(found, key=lambda p: p.number)


def get(problem_id: str) -> Problem:
    path = config.ALGO_DIR / problem_id
    if "/" in problem_id or "\\" in problem_id or ".." in problem_id or not _is_ready(path):
        raise ProblemNotFound(problem_id)
    return _load(path)


# -- content -----------------------------------------------------------------------------
def _md(problem: Problem, name: str) -> str:
    return render_markdown((problem.path / name).read_text(encoding="utf-8"))


def statement_html(problem: Problem) -> str:
    return _md(problem, "statement.md")


def hints_html(problem: Problem) -> str:
    return _md(problem, "hints.md")


# explanation.md doesn't repeat the reference solution: an empty ```solution block marks where
# solution.py goes, so the explanation shows the one, fully commented copy.
SOLUTION_MARKER = re.compile(r"^```solution[ \t]*\r?\n```[ \t]*$", re.M)


def expand_solution(text: str, code: str) -> str:
    """explanation.md with its ```solution marker replaced by solution.py as a python block."""
    block = "```python\n" + code.strip("\n") + "\n```"
    return SOLUTION_MARKER.sub(lambda _: block, text)


def explanation_markdown(problem: Problem) -> str:
    text = (problem.path / "explanation.md").read_text(encoding="utf-8")
    return expand_solution(text, solution_code(problem))


def explanation_html(problem: Problem) -> str:
    return render_markdown(explanation_markdown(problem))


def solution_code(problem: Problem) -> str:
    return (problem.path / "solution.py").read_text(encoding="utf-8")


def foundations_dir() -> Path:
    return config.ALGO_DIR / "foundations"


def foundation_links(problem: Problem) -> list[dict]:
    return pages.links(foundations_dir(), "#/algo/learn", problem.foundations)


# -- tests -------------------------------------------------------------------------------
def _test_data(problem: Problem) -> dict:
    return json.loads((problem.path / "tests.json").read_text(encoding="utf-8"))


def tests(problem: Problem, include_hidden: bool) -> list[dict]:
    """Runner tests: one step each, calling the method with the case's arguments."""
    data = _test_data(problem)
    out = []
    for visibility in ("shown", "hidden") if include_hidden else ("shown",):
        for case in data[visibility]:
            test = {
                "id": case["id"],
                "name": case.get("name") or case["id"],
                "visibility": visibility,
                "steps": [{"call": problem.method, "args": case["args"], "expect": case["expect"]}],
            }
            if case.get("limit_ms"):
                test["limit_ms"] = case["limit_ms"]
            out.append(test)
    return out


def shown_cases(problem: Problem) -> list[dict]:
    """The examples a session shows before anything runs: name, arguments, expected result."""
    return [
        {"id": c["id"], "name": c.get("name") or c["id"], "args": c["args"], "expect": c["expect"]}
        for c in _test_data(problem)["shown"]
    ]


def param_names(problem: Problem) -> list[str]:
    params = re.search(r"\((.*)\)", problem.signature).group(1)
    names = [p.split(":")[0].split("=")[0].strip() for p in params.split(",")]
    return [n for n in names if n and n != "self"]


def starter_code(problem: Problem) -> str:
    """solution.py for a new session: typing imports, node classes, the empty method."""
    typing = [name for name in ("List", "Optional") if f"{name}[" in problem.signature]
    parts = [f"from typing import {', '.join(typing)}\n" if typing else ""]
    kinds = [*(problem.adapters.get("args") or []), problem.adapters.get("result")]
    seen = set()
    for kind in kinds:
        cls = NODE_CLASSES.get(kind)
        if cls and cls not in seen:
            seen.add(cls)
            parts.append(cls)
    parts.append(f"class Solution:\n    {problem.signature.strip()}\n        pass\n")
    return "\n\n".join(p for p in parts if p).replace("\n\n\n\n", "\n\n\n")


HELPERS = {
    "listnode": "make_list",
    "listnodes": "make_lists",
    "tree": "make_tree",
    "graph": "make_graph",
}
SHOW = {"listnode": "list_values", "tree": "tree_values", "graph": "graph_values"}


def scratch_starter(problem: Problem) -> str:
    """scratch.py for a new session: calls the method on the first example and prints the result.

    Problems on linked lists, trees or graphs import builders from helpers.py (scratch_helpers.py,
    copied next to solution.py when scratch runs).
    """
    first = next(iter(_test_data(problem)["shown"]), None)
    arg_kinds = list(problem.adapters.get("args") or [])
    in_place = problem.adapters.get("check") == "arg0"
    shown_kind = arg_kinds[0] if in_place and arg_kinds else problem.adapters.get("result")
    needed = [HELPERS[k] for k in arg_kinds if k in HELPERS]
    if shown_kind in SHOW:
        needed.append(SHOW[shown_kind])
    lines = ["# Scratch: try your solution here. Run executes this file and shows what it prints."]
    if needed:
        names = ", ".join(dict.fromkeys(needed))
        lines.append(f"from helpers import {names}  # build lists, trees and graphs from lists")
    lines += ["from solution import *  # noqa: F403", ""]
    if first is None:
        return "\n".join(lines) + "\n"
    names = param_names(problem)[: len(first["args"])]
    for i, (name, value) in enumerate(zip(names, first["args"], strict=False)):
        kind = arg_kinds[i] if i < len(arg_kinds) else None
        built = f"{HELPERS[kind]}({value!r})" if kind in HELPERS else repr(value)
        lines.append(f"{name} = {built}")
    call = f"Solution().{problem.method}({', '.join(names)})"
    if in_place:
        lines += [call, f"print({SHOW.get(shown_kind, '')}({names[0]}))"]
    elif shown_kind in SHOW:
        lines += [f"result = {call}", f"print({SHOW[shown_kind]}(result))"]
    else:
        lines += [f"result = {call}", "print(result)"]
    lines.append(f"# expected: {first['expect']!r}")
    return "\n".join(lines) + "\n"
