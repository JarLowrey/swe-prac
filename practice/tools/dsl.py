"""Parser for the test authoring format used in reference/<problem>/tests.txt.

A tests.txt file is a sequence of test blocks. Each block runs on a fresh instance:

    === L1 shown: basic add, get, delete
    add_file(1, "/a.txt", 10) -> True
    add_file(2, "/a.txt", 5) -> False      # comment
    add_file(3, "/b", 1); add_file(4, "/c", 2)
    get_file_size(5, "/b") -> ?

    === L2 hidden: long random sequence @gen(seed=7, n=300)

Rules:
  * Header: `=== L<level> <shown|hidden>: <name>`, optionally ending in `@gen(k=v, ...)`,
    which asks reference/<problem>/gen.py for the steps (all golden).
  * A step is a Python call with literal arguments. `-> <literal>` checks the return value,
    `-> ?` checks it against the reference solution's value (golden), and no arrow means
    the return value is not checked (the call must still not raise).
  * Several steps may share a line, separated by `;`. `#` starts a comment.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

GOLDEN = object()  # sentinel: expected value comes from the reference solution
UNCHECKED = object()  # sentinel: return value is not checked

HEADER_RE = re.compile(
    r"^===\s*L(?P<level>[1-4])\s+(?P<vis>shown|hidden)\s*:\s*(?P<name>.*?)"
    r"(?:\s+@gen\((?P<gen>[^)]*)\))?\s*$"
)


@dataclass
class Step:
    call: str
    args: list
    expect: object  # a literal, GOLDEN or UNCHECKED
    line: int = 0


@dataclass
class TestBlock:
    level: int
    visibility: str
    name: str
    line: int
    steps: list[Step] = field(default_factory=list)
    gen: dict | None = None


class DSLError(ValueError):
    pass


def split_outside_quotes(text: str, sep: str) -> list[str]:
    """Split on `sep` wherever it is not inside a string literal."""
    parts, buf, quote, i = [], [], None, 0
    while i < len(text):
        ch = text[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and i + 1 < len(text):
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif text.startswith(sep, i):
            parts.append("".join(buf))
            buf = []
            i += len(sep)
            continue
        else:
            buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


def strip_comment(line: str) -> str:
    return split_outside_quotes(line, "#")[0]


def parse_literal(text: str, where: str):
    try:
        return ast.literal_eval(text.strip())
    except (ValueError, SyntaxError) as exc:
        raise DSLError(f"{where}: not a Python literal: {text.strip()!r}") from exc


def parse_step(text: str, line_no: int) -> Step:
    where = f"line {line_no}"
    pieces = split_outside_quotes(text, "->")
    if len(pieces) > 2:
        raise DSLError(f"{where}: more than one '->' in step {text!r}")
    call_src = pieces[0].strip()
    try:
        node = ast.parse(call_src, mode="eval").body
    except SyntaxError as exc:
        raise DSLError(f"{where}: cannot parse call {call_src!r}") from exc
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.keywords:
        raise DSLError(f"{where}: expected `method(arg, ...)`, got {call_src!r}")
    try:
        args = [ast.literal_eval(a) for a in node.args]
    except ValueError as exc:
        raise DSLError(f"{where}: arguments must be literals in {call_src!r}") from exc
    if len(pieces) == 1:
        expect = UNCHECKED
    elif pieces[1].strip() == "?":
        expect = GOLDEN
    else:
        expect = parse_literal(pieces[1], where)
    return Step(call=node.func.id, args=args, expect=expect, line=line_no)


def parse_gen_args(text: str, where: str) -> dict:
    out = {}
    for part in filter(None, (p.strip() for p in text.split(","))):
        if "=" not in part:
            raise DSLError(f"{where}: @gen arguments must be key=value, got {part!r}")
        key, value = part.split("=", 1)
        out[key.strip()] = parse_literal(value, where)
    return out


def parse_tests(source: str) -> list[TestBlock]:
    blocks: list[TestBlock] = []
    current: TestBlock | None = None
    for line_no, raw in enumerate(source.splitlines(), start=1):
        if raw.startswith("==="):
            m = HEADER_RE.match(raw.strip())
            if not m:
                raise DSLError(f"line {line_no}: bad header {raw!r}")
            current = TestBlock(
                level=int(m["level"]),
                visibility=m["vis"],
                name=m["name"].strip() or f"test at line {line_no}",
                line=line_no,
                gen=parse_gen_args(m["gen"], f"line {line_no}") if m["gen"] is not None else None,
            )
            blocks.append(current)
            continue
        body = strip_comment(raw).strip()
        if not body:
            continue
        if current is None:
            raise DSLError(f"line {line_no}: step before the first '===' header")
        for piece in split_outside_quotes(body, ";"):
            if piece.strip():
                current.steps.append(parse_step(piece, line_no))
    return blocks


def format_value(value) -> str:
    return repr(value)


def format_step(step: Step) -> str:
    call = f"{step.call}({', '.join(repr(a) for a in step.args)})"
    if step.expect is UNCHECKED:
        return call
    if step.expect is GOLDEN:
        return f"{call} -> ?"
    return f"{call} -> {step.expect!r}"
