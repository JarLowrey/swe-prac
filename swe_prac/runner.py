"""Standalone test harness, executed in a fresh subprocess for every Run/Submit.

Usage: python -I runner.py <solution.py> <ClassName> <tests.json> <results.jsonl>

It imports the solution file, then runs each test on a fresh instance of the class.
Results are appended to the results file as JSON lines and flushed after each event,
so the parent process can recover partial results if this process is killed on timeout.

This file must stay self-contained (stdlib only, no package imports): it runs with -I.

The tests file may carry "options" (the algorithms track uses them; the coding track doesn't):

    adapters        {"args": [kind | null, ...], "result": kind | null, "check": "result" | "arg0"}
                    Kinds turn JSON into the structures the method takes, and back:
                    "listnode"  [1, 2, 3]            <-> linked list of ListNode
                    "listnodes" [[1, 4], [2]]         -> a list of linked lists (arguments only)
                    "tree"      [3, 9, 20, null, 7]  <-> binary tree of TreeNode (level order)
                    "graph"     [[2, 4], [1, 3], ...] <-> graph of Node, node i+1's neighbours
                    "check": "arg0" compares the first argument after the call (in-place
                    methods that return None) instead of the return value.
    compare         "exact" (default), "unordered" (any order), "unordered_nested" (any order,
                    inside and out), or "validator".
    validator       Python source defining check(args, expect, actual) -> bool | str, used when
                    several answers are right (any valid order, any longest palindrome...).
    normalize       Treat tuples in the result as lists.
    deep_recursion  Run each call in a thread with a large stack and a high recursion limit, so
                    recursive (top-down memoised) solutions work on large inputs.

A test may also set "limit_ms": the call fails if it takes longer (a too-slow algorithm). A call
still running at LIMIT_GRACE times its limit is abandoned and the run stops there ("stopped"
event), since a thread can't be interrupted; tests after it are reported as not run.
"""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
import sys
import threading
import time
import traceback
from collections import deque

MAX_STDOUT_CHARS = 20_000
MAX_REPR_CHARS = 2_000
MAX_NODES = 1_000_000
DEEP_STACK_BYTES = 64 * 1024 * 1024
DEEP_RECURSION_LIMIT = 200_000
LIMIT_GRACE = 1.5


def decode(value):
    """Decode JSON test data; {"__tuple__": [...]} becomes a tuple."""
    if isinstance(value, dict):
        if set(value) == {"__tuple__"}:
            return tuple(decode(v) for v in value["__tuple__"])
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


def short_repr(value) -> str:
    try:
        text = repr(value)
    except Exception as exc:  # a user object with a broken __repr__
        text = f"<unrepresentable {type(value).__name__}: {exc}>"
    if len(text) > MAX_REPR_CHARS:
        text = text[:MAX_REPR_CHARS] + "...<truncated>"
    return text


def matches(expected, actual) -> bool:
    """Strict-ish equality: bools must be bools, None must be None, ints may be equal floats."""
    if expected is None:
        return actual is None
    if isinstance(expected, bool):
        return isinstance(actual, bool) and actual == expected
    if isinstance(expected, (int, float)):
        if isinstance(actual, bool) or not isinstance(actual, (int, float)):
            return False
        return actual == expected
    if isinstance(expected, str):
        return isinstance(actual, str) and actual == expected
    return type(actual) is type(expected) and actual == expected


# -- data-structure arguments (algorithms track) -----------------------------------------
class ListNode:
    def __init__(self, val=0, next=None):  # noqa: A002 - the conventional name
        self.val = val
        self.next = next


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class Node:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []


class AdapterError(Exception):
    """The method returned something that isn't a well-formed list, tree or graph."""


def _node(cls, fallback, val):
    """A node of the solution's own class when it defines one (so isinstance checks work)."""
    try:
        return cls(val)
    except Exception:
        return fallback(val)


def to_listnode(values, cls=ListNode):
    head = None
    for value in reversed(values):
        node = _node(cls, ListNode, value)
        node.next = head
        head = node
    return head


def from_listnode(head) -> list:
    out, seen = [], set()
    while head is not None:
        if id(head) in seen:
            raise AdapterError("The linked list loops back on itself (it has a cycle).")
        if len(out) >= MAX_NODES:
            raise AdapterError("The linked list is too long.")
        seen.add(id(head))
        out.append(head.val)
        head = getattr(head, "next", None)
    return out


def to_tree(values, cls=TreeNode):
    """The usual level order: [1, null, 2, 3] is 1 with right child 2, whose left is 3."""
    if not values or values[0] is None:
        return None

    def make(value):
        node = _node(cls, TreeNode, value)
        node.left = node.right = None
        return node

    root = make(values[0])
    queue = deque([root])
    i = 1
    while queue and i < len(values):
        parent = queue.popleft()
        for side in ("left", "right"):
            if i < len(values) and values[i] is not None:
                child = make(values[i])
                setattr(parent, side, child)
                queue.append(child)
            i += 1
    return root


def from_tree(root) -> list:
    out, seen = [], set()
    queue = deque([root])
    while queue:
        node = queue.popleft()
        if node is None:
            out.append(None)
            continue
        if id(node) in seen:
            raise AdapterError("That isn't a tree: a node is reachable twice.")
        if len(seen) >= MAX_NODES:
            raise AdapterError("The tree is too large.")
        seen.add(id(node))
        out.append(node.val)
        queue.append(getattr(node, "left", None))
        queue.append(getattr(node, "right", None))
    while out and out[-1] is None:
        out.pop()
    return out


def to_graph(adjacency, cls=Node):
    """Node i+1's neighbours are adjacency[i]; returns node 1, or None for an empty graph."""
    nodes = [_node(cls, Node, i + 1) for i in range(len(adjacency))]
    for node, neighbours in zip(nodes, adjacency, strict=True):
        node.neighbors = [nodes[v - 1] for v in neighbours]
    return nodes[0] if nodes else None


def graph_nodes(start) -> list:
    out, seen = [], set()
    queue = deque([start] if start is not None else [])
    while queue:
        node = queue.popleft()
        if id(node) in seen:
            continue
        if len(seen) >= MAX_NODES:
            raise AdapterError("The graph is too large.")
        seen.add(id(node))
        out.append(node)
        queue.extend(getattr(node, "neighbors", None) or [])
    return out


def from_graph(start) -> list:
    nodes = graph_nodes(start)
    by_val = {}
    for node in nodes:
        if node.val in by_val:
            raise AdapterError(f"Two nodes have the value {node.val!r}.")
        by_val[node.val] = node
    if sorted(by_val, key=repr) != sorted(range(1, len(nodes) + 1), key=repr):
        raise AdapterError("Node values must be 1..n, like the input's.")
    return [[n.val for n in by_val[v].neighbors] for v in range(1, len(nodes) + 1)]


def adapt_arg(kind, value, module):
    if kind is None:
        return value
    if kind == "listnode":
        return to_listnode(value, getattr(module, "ListNode", ListNode))
    if kind == "listnodes":
        return [to_listnode(v, getattr(module, "ListNode", ListNode)) for v in value]
    if kind == "tree":
        return to_tree(value, getattr(module, "TreeNode", TreeNode))
    if kind == "graph":
        return to_graph(value, getattr(module, "Node", Node))
    raise ValueError(f"unknown adapter {kind!r}")


def adapt_result(kind, value):
    if kind is None:
        return value
    if value is not None and not hasattr(value, "val"):
        raise AdapterError(f"Expected a node (or None), got {short_repr(value)}.")
    if kind == "listnode":
        return from_listnode(value)
    if kind == "tree":
        return from_tree(value)
    if kind == "graph":
        return from_graph(value)
    raise ValueError(f"unknown adapter {kind!r}")


def plain(value):
    """Tuples (anywhere in the result) become lists, so `return (i, j)` matches [i, j]."""
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def _sort_key(value) -> str:
    return json.dumps(value, sort_keys=True, default=repr)


def compare(options: dict, raw_args, expect, actual, checker) -> tuple[bool, str | None]:
    """(passed, message): message explains a failure the values alone don't show."""
    mode = options.get("compare", "exact")
    if mode == "exact":
        return matches(expect, actual), None
    if mode in ("unordered", "unordered_nested"):
        if not isinstance(actual, list):
            return False, None
        if mode == "unordered_nested":
            if not all(isinstance(x, list) for x in actual):
                return False, None
            actual = [sorted(x, key=_sort_key) for x in actual]
            expect = [sorted(x, key=_sort_key) for x in expect]
        return matches(sorted(expect, key=_sort_key), sorted(actual, key=_sort_key)), None
    if mode == "validator":
        verdict = checker(raw_args, expect, actual)
        if isinstance(verdict, str):
            return False, verdict
        return bool(verdict), None
    raise ValueError(f"unknown compare mode {mode!r}")


class TooSlow(Exception):
    """The call was still running when its time limit (with grace) ran out."""


def call(method, args, deep: bool, timeout: float | None = None, timing: dict | None = None):
    """Call the method. With deep=True or a timeout, in a thread: a large stack allows deep
    recursion, and a call running past `timeout` seconds raises TooSlow (it keeps running).

    With `timing`, timing["ms"] is set to how long the method itself ran. It's measured in the
    thread that runs it: starting a thread with a large stack can take tens of milliseconds on a
    busy machine, and that isn't the solution's time. (Thread.start() returns once the thread
    runs, so `timeout` doesn't include it either.)"""
    if timing is None:
        timing = {}
    if not deep and timeout is None:
        started = time.perf_counter()
        try:
            return method(*args)
        finally:
            timing["ms"] = (time.perf_counter() - started) * 1000
    box: dict = {}

    def target():
        started = time.perf_counter()
        try:
            box["value"] = method(*args)
        except BaseException as exc:  # re-raised in the caller's thread
            box["error"] = exc
        finally:
            timing["ms"] = (time.perf_counter() - started) * 1000

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise TooSlow
    if "error" in box:
        raise box["error"]
    return box.get("value")


def user_traceback(exc: BaseException, solution_path: str) -> str:
    """Format a traceback, keeping only frames from the user's solution file."""
    frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == solution_path]
    lines = ["Traceback (most recent call last):\n"]
    lines += traceback.format_list(frames)
    lines += traceback.format_exception_only(type(exc), exc)
    # Show "solution.py" (the editor's file name), not the session's absolute path.
    return "".join(lines).replace(solution_path, "solution.py")


class LimitedBuffer(io.StringIO):
    def write(self, s):
        remaining = MAX_STDOUT_CHARS - self.tell()
        if remaining <= 0:
            return len(s)
        if len(s) > remaining:
            super().write(s[:remaining] + "\n...<output truncated>\n")
            return len(s)
        return super().write(s)


def main() -> int:
    solution_path, class_name, tests_path, results_path = sys.argv[1:5]
    with open(tests_path, encoding="utf-8") as fh:
        data = decode(json.load(fh))
    tests, options = data["tests"], data.get("options") or {}
    adapters = options.get("adapters") or {}
    arg_kinds = adapters.get("args") or []
    result_kind = adapters.get("result")
    check_arg0 = adapters.get("check") == "arg0"
    deep = bool(options.get("deep_recursion"))
    checker = None
    if options.get("compare") == "validator":
        namespace: dict = {}
        exec(compile(options["validator"], "<checker>", "exec"), namespace)  # problem's own file
        checker = namespace["check"]
    if deep:
        sys.setrecursionlimit(DEEP_RECURSION_LIMIT)
        threading.stack_size(DEEP_STACK_BYTES)
    out = open(results_path, "a", encoding="utf-8")  # noqa: SIM115 - kept open for streaming

    def emit(event: dict) -> None:
        out.write(json.dumps(event) + "\n")
        out.flush()

    buffer = LimitedBuffer()
    try:
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            spec = importlib.util.spec_from_file_location("solution", solution_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules["solution"] = module
            spec.loader.exec_module(module)
        cls = getattr(module, class_name, None)
        if cls is None:
            emit(
                {
                    "event": "import_error",
                    "error": f"Your code must define a class named `{class_name}`.",
                    "stdout": buffer.getvalue(),
                }
            )
            return 0
    except BaseException as exc:  # SyntaxError, ImportError, SystemExit...
        if isinstance(exc, SyntaxError):
            err = "".join(traceback.format_exception_only(type(exc), exc)).replace(
                solution_path, "solution.py"
            )
        else:
            err = user_traceback(exc, solution_path)
        emit({"event": "import_error", "error": err, "stdout": buffer.getvalue()})
        return 0

    stop = None
    for test in tests:
        if stop:
            break
        emit({"event": "start", "id": test["id"]})
        buffer = LimitedBuffer()
        steps_out = []
        passed = True
        error = None
        failed_step = None
        started = time.perf_counter()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            try:
                obj = cls()
            except BaseException as exc:
                passed = False
                error = "Error constructing the class:\n" + user_traceback(exc, solution_path)
                obj = None
            for index, step in enumerate(test["steps"] if obj is not None else []):
                name, raw_args = step["call"], step["args"]
                record = {
                    "call": name,
                    "args": ", ".join(short_repr(a) for a in raw_args),
                    "checked": "expect" in step,
                }
                if "expect" in step:
                    record["expect"] = short_repr(step["expect"])
                method = getattr(obj, name, None)
                if not callable(method):
                    record["ok"] = False
                    record["actual"] = "<method not defined>"
                    steps_out.append(record)
                    passed, failed_step = False, index
                    error = f"Method `{name}` is not defined on `{class_name}`."
                    break
                # The method may mutate its arguments; keep pristine copies for the checks.
                pristine = copy.deepcopy(raw_args) if options else raw_args
                args = [
                    adapt_arg(arg_kinds[i] if i < len(arg_kinds) else None, a, module)
                    for i, a in enumerate(copy.deepcopy(raw_args) if options else raw_args)
                ]
                originals = (
                    {id(n) for n in graph_nodes(args[0])}
                    if result_kind == "graph" and arg_kinds[:1] == ["graph"]
                    else set()
                )
                limit = test.get("limit_ms")
                stop_after = limit * LIMIT_GRACE / 1000 if limit else None
                timing: dict = {}
                try:
                    actual = call(method, args, deep, stop_after, timing)
                except TooSlow:
                    record["ok"] = False
                    record["actual"] = "<stopped: too slow>"
                    steps_out.append(record)
                    passed, failed_step = False, index
                    error = (
                        f"Too slow: stopped after {limit * LIMIT_GRACE:,.0f} ms; the limit for "
                        f"this test is {limit:,} ms. Look for a faster algorithm."
                    )
                    stop = error
                    break
                except BaseException as exc:
                    record["ok"] = False
                    record["actual"] = f"<raised {type(exc).__name__}>"
                    steps_out.append(record)
                    passed, failed_step = False, index
                    error = user_traceback(exc, solution_path)
                    break
                call_ms = timing["ms"]
                message = None
                try:
                    if check_arg0:
                        actual = adapt_result(arg_kinds[0] if arg_kinds else None, args[0])
                    else:
                        if originals and any(id(n) in originals for n in graph_nodes(actual)):
                            raise AdapterError(
                                "The copy reuses nodes of the original graph: clone every node."
                            )
                        actual = adapt_result(result_kind, actual)
                    if options.get("normalize"):
                        actual = plain(actual)
                except AdapterError as exc:
                    actual, message = f"<{exc}>", str(exc)
                record["actual"] = short_repr(actual)
                if message is not None:
                    record["ok"] = False
                elif "expect" not in step:
                    record["ok"] = True
                elif options:
                    record["ok"], message = compare(
                        options, pristine, step["expect"], actual, checker
                    )
                else:
                    record["ok"] = matches(step["expect"], actual)
                if record["ok"] and limit and call_ms > limit:
                    record["ok"] = False
                    message = (
                        f"Too slow: this test took {call_ms:,.0f} ms and the limit is "
                        f"{limit:,} ms. The answer was right; look for a faster algorithm."
                    )
                steps_out.append(record)
                if not record["ok"]:
                    passed, failed_step = False, index
                    error = message
                    break
        emit(
            {
                "event": "end",
                "id": test["id"],
                "passed": passed,
                "steps": steps_out,
                "total_steps": len(test["steps"]),
                "failed_step": failed_step,
                "error": error,
                "stdout": buffer.getvalue(),
                "ms": round((time.perf_counter() - started) * 1000, 2),
            }
        )
    if stop:
        # The slow call is still running in its thread and can't be interrupted: report what
        # happened and leave without waiting for it.
        emit({"event": "stopped", "reason": stop})
        out.close()
        os._exit(0)
    emit({"event": "done"})
    out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
