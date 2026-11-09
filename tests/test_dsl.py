from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import dsl  # noqa: E402


def test_parse_blocks_and_steps():
    src = """
# leading comment
=== L1 shown: basics
add(1, "a;b", 2) -> True   # semicolon inside a string
add(2, "x") ; get(3, "x") -> None
get(4, "# not a comment") -> ?

=== L3 hidden: random @gen(seed=7, n=50)
"""
    blocks = dsl.parse_tests(src)
    assert [(b.level, b.visibility, b.name) for b in blocks] == [
        (1, "shown", "basics"),
        (3, "hidden", "random"),
    ]
    steps = blocks[0].steps
    assert steps[0].args == [1, "a;b", 2] and steps[0].expect is True
    assert steps[1].expect is dsl.UNCHECKED
    assert steps[2].expect is None
    assert steps[3].args == [4, "# not a comment"] and steps[3].expect is dsl.GOLDEN
    assert blocks[1].gen == {"seed": 7, "n": 50}


def test_tuples_and_arrow_in_string():
    step = dsl.parse_step('place(5, [("A", 2), ("B", 1)]) -> "a->b"', 1)
    assert step.args == [5, [("A", 2), ("B", 1)]]
    assert step.expect == "a->b"


@pytest.mark.parametrize(
    "bad",
    [
        "=== L5 shown: no such level",
        "=== L1 shown: x\nadd(1, x) -> 1",  # non-literal argument
        "add(1) -> 1",  # step before header
        "=== L1 shown: x\nadd(1, k=2)",  # keyword args
    ],
)
def test_errors(bad):
    with pytest.raises(dsl.DSLError):
        dsl.parse_tests(bad)
