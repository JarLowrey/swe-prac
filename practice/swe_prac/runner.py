"""The test harness. It imports a solution file, then runs each test on a fresh instance of the
class, reporting one event per test as it goes.

It runs in two places, and must stay self-contained (stdlib only, no package imports) for both:

* In the browser, for every Run and Submit: the app's Web Worker (static/py-worker.js) loads
  this file into Pyodide, a fresh interpreter each time, and calls browser_tests(). Events go
  to the page as they happen, so when the page stops a runaway run it still has the results of
  the tests that finished. browser_scratch() runs scratch.py the same way.
* Natively, in a subprocess, when tools/build_problem.py and tools/build_algo.py check a
  problem (swe_prac/execution.py):

      python -I runner.py <solution.py> <ClassName> <tests.json> <results.jsonl>

  Events are appended to the results file as JSON lines and flushed after each one, so the
  parent process can recover partial results if it kills this process on a timeout.

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
    deep_recursion  A high recursion limit, so recursive (top-down memoised) solutions work on
                    large inputs. Natively each call also runs in a thread with a large stack.

A test may also set "limit_ms": the call fails if it takes longer (a too-slow algorithm). A call
still running at LIMIT_GRACE times its limit is abandoned and the run stops there; tests after it
are reported as not run. Natively the call runs in a thread, which can't be interrupted, so the
runner reports a "stopped" event and exits. The browser has no threads: there the runner emits a
"call" event just before the call and the page ends the worker if the call outlives its limit.
"""

from __future__ import annotations

import builtins
import contextlib
import copy
import importlib.util
import io
import json
import os
import runpy
import sys
import threading
import time
import traceback
import types
from collections import deque

MAX_STDOUT_CHARS = 20_000
MAX_REPR_CHARS = 2_000
MAX_NODES = 1_000_000
DEEP_STACK_BYTES = 64 * 1024 * 1024
DEEP_RECURSION_LIMIT = 200_000
LIMIT_GRACE = 1.5
MAX_SCRATCH_CHARS = 50_000
MAX_TRACEBACK_FRAMES = 30
# scratch.py runs natively with Python's default limit, 1000. In the browser the pure-Python
# functools.cache (see install_browser_shims) takes two frames per level, so allow a little more.
SCRATCH_RECURSION_LIMIT = 3_000
# Pyodide can't start threads, so in the browser every call runs inline (see call()).
THREADS = sys.platform != "emscripten"


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
    runs, so `timeout` doesn't include it either.)

    Without threads (the browser) the call always runs inline: `deep` only raises the recursion
    limit (run() does that), and the page enforces `timeout` by ending the worker."""
    if timing is None:
        timing = {}
    if not THREADS or (not deep and timeout is None):
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
    """Format a traceback, keeping only frames from the user's solution file, and only the last
    MAX_TRACEBACK_FRAMES of those: a runaway recursion has 200,000, and formatting them all takes
    seconds."""
    mine = []
    tb = exc.__traceback__
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == solution_path:
            mine.append(tb)
        tb = tb.tb_next
    hidden = max(0, len(mine) - MAX_TRACEBACK_FRAMES)
    start = mine[hidden] if mine else None
    frames = [f for f in traceback.extract_tb(start) if f.filename == solution_path]
    lines = ["Traceback (most recent call last):\n"]
    if hidden:
        lines.append(f"  ... {hidden:,} earlier calls not shown\n")
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


def run(solution_path: str, class_name: str, data: dict, emit) -> str | None:
    """Run data["tests"] against the solution, calling emit(event) for each event.

    Returns why the run stopped early (a call past its time limit, still running in its thread),
    or None. The events: "import_error"; per test "start", "call" (browser only, just before a
    call that has a time limit) and "end"; then "stopped" or "done".
    """
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
        if THREADS:
            threading.stack_size(DEEP_STACK_BYTES)

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
            return None
    except BaseException as exc:  # SyntaxError, ImportError, SystemExit...
        if isinstance(exc, SyntaxError):
            err = "".join(traceback.format_exception_only(type(exc), exc)).replace(
                solution_path, "solution.py"
            )
        else:
            err = user_traceback(exc, solution_path)
        emit({"event": "import_error", "error": err, "stdout": buffer.getvalue()})
        return None

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
                keep(obj, args)
                originals = (
                    {id(n) for n in graph_nodes(args[0])}
                    if result_kind == "graph" and arg_kinds[:1] == ["graph"]
                    else set()
                )
                limit = test.get("limit_ms")
                stop_after = limit * LIMIT_GRACE / 1000 if limit else None
                timing: dict = {}
                if limit and not THREADS:
                    emit({"event": "call", "id": test["id"], "limit_ms": limit})
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
                keep(actual)
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
        emit({"event": "stopped", "reason": stop})
        return stop
    emit({"event": "done"})
    return None


def main() -> int:
    """Native entry point (a subprocess per run): events go to the results file."""
    solution_path, class_name, tests_path, results_path = sys.argv[1:5]
    with open(tests_path, encoding="utf-8") as fh:
        data = decode(json.load(fh))
    out = open(results_path, "a", encoding="utf-8")  # noqa: SIM115 - kept open for streaming

    def emit(event: dict) -> None:
        out.write(json.dumps(event) + "\n")
        out.flush()

    stop = run(solution_path, class_name, data, emit)
    out.close()
    if stop:
        # The slow call is still running in its thread and can't be interrupted: leave without
        # waiting for it.
        os._exit(0)
    return 0


# -- the browser (Pyodide) ---------------------------------------------------------------
# Recursion that passes through C code uses the JavaScript engine's stack, which in a Web Worker
# overflows after a few hundred levels and takes the whole interpreter down with it. Natively,
# deep_recursion gives each call a 64 MB thread stack instead, but the browser has no threads.
# So in the browser, the C code that recursive solutions most often recurse through is swapped
# for pure-Python equivalents, which recurse inside the interpreter, where only
# sys.setrecursionlimit bounds them: functools.cache and lru_cache, and max, min, sum, any, all
# and sorted when they are given a generator (`1 + max(depth(c) for c in node.children)`).
_SHIMMED = ("max", "min", "sum", "any", "all", "sorted")
_ORIGINAL = {name: getattr(builtins, name) for name in _SHIMMED}
_GENERATOR = types.GeneratorType

# Freeing has the same problem: CPython frees a long linked list or a deep tree by recursing in
# C, which takes the interpreter down from about 10,000 nodes (CPython's own guard against this
# measures a different stack under WebAssembly). So in the browser every test's arguments and
# results are kept alive: the worker is thrown away after the run, so they never need freeing.
_kept: list | None = None  # natively None: nothing is kept


def keep(*objects) -> None:
    if _kept is not None:
        _kept.append(objects)


def _drain(generator) -> list:
    """The generator's items, consumed by Python's own loop instead of by C code."""
    items = []
    for item in generator:
        items.append(item)
    return items


def _draining(name: str, alone: bool):
    """The builtin `name`, but a generator first argument is drained in Python first. With
    alone=True (max, min) only a lone positional argument is an iterable."""
    original = _ORIGINAL[name]

    def shim(*args, **kwargs):
        if args and type(args[0]) is _GENERATOR and (len(args) == 1 or not alone):
            args = (_drain(args[0]), *args[1:])
        return original(*args, **kwargs)

    shim.__name__ = shim.__qualname__ = name
    shim.__doc__ = original.__doc__
    return shim


def _short_circuit(name: str, wanted: bool):
    """any (wanted=True) or all (wanted=False), stopping at the first deciding item, as they do."""
    original = _ORIGINAL[name]

    def shim(iterable, /):
        if type(iterable) is not _GENERATOR:
            return original(iterable)
        for item in iterable:
            if bool(item) is wanted:
                return wanted
        return not wanted

    shim.__name__ = shim.__qualname__ = name
    shim.__doc__ = original.__doc__
    return shim


def pure_functools() -> types.ModuleType:
    """A copy of functools built without its C accelerator, _functools: its lru_cache is the
    standard library's own pure-Python one (PEP 399 requires that it exists)."""
    spec = importlib.util.find_spec("functools")
    saved = sys.modules.get("_functools")
    sys.modules["_functools"] = None  # `from _functools import ...` now raises ImportError
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if saved is None:
            del sys.modules["_functools"]
        else:
            sys.modules["_functools"] = saved
    return module


def install_browser_shims() -> None:
    """Swap in the pure-Python versions above. Only for the browser: it changes builtins."""
    import functools

    pure = pure_functools()
    functools.lru_cache, functools.cache = pure.lru_cache, pure.cache
    for name, alone in (("max", True), ("min", True), ("sum", False), ("sorted", False)):
        setattr(builtins, name, _draining(name, alone))
    builtins.any = _short_circuit("any", True)
    builtins.all = _short_circuit("all", False)
    sys.stdin = io.StringIO("")  # input() raises EOFError, as with a subprocess that has no input


def browser_tests(solution_path: str, class_name: str, payload: str, post) -> None:
    """Run the tests in `payload` (JSON: {"tests": [...], "options": {...}}) against the solution,
    calling post(text) with each event as JSON. static/py-worker.js calls this."""
    global _kept
    install_browser_shims()
    if _kept is None:  # never replaced: dropping the old list would free what it holds
        _kept = []
    run(solution_path, class_name, decode(json.loads(payload)), lambda e: post(json.dumps(e)))


class _Stream(io.TextIOBase):
    """sys.stdout or sys.stderr for scratch.py: hands text to the page in batches (at most every
    50 ms, so a print loop doesn't flood it), up to MAX_SCRATCH_CHARS in all."""

    def __init__(self, post):
        self.post = post
        self.left = MAX_SCRATCH_CHARS
        self.pending: list[str] = []
        self.flushed_at = time.perf_counter()

    def writable(self) -> bool:
        return True

    def write(self, s: str) -> int:
        if self.left > 0 and s:
            chunk = s[: self.left]
            self.left -= len(chunk)
            self.pending.append(chunk)
            if time.perf_counter() - self.flushed_at > 0.05:
                self.flush()
        return len(s)

    def flush(self) -> None:
        if self.pending:
            self.post("".join(self.pending))
            self.pending.clear()
        self.flushed_at = time.perf_counter()


def browser_scratch(workdir: str, script: str, post_out, post_err) -> int:
    """Run `script` (scratch.py, in `workdir` beside solution.py) as a program; returns its exit
    code. Its output goes to post_out / post_err as it's printed. static/py-worker.js calls this."""
    install_browser_shims()
    sys.setrecursionlimit(SCRATCH_RECURSION_LIMIT)
    os.chdir(workdir)
    sys.path.insert(0, workdir)
    out, err = _Stream(post_out), _Stream(post_err)
    sys.stdout, sys.stderr = out, err
    code = 0
    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit as exc:
        if exc.code is None or isinstance(exc.code, int):
            code = int(exc.code or 0)
        else:
            err.write(f"{exc.code}\n")
            code = 1
    except BaseException as exc:
        # Like an uncaught error in a program: the traceback from the script's own frame on,
        # with file names as the editor shows them.
        tb = exc.__traceback__
        while tb is not None and tb.tb_frame.f_code.co_filename != script:
            tb = tb.tb_next
        text = "".join(traceback.format_exception(type(exc), exc, tb))
        err.write(text.replace(workdir.rstrip("/") + "/", ""))
        code = 1
    finally:
        out.flush()
        err.flush()
    return code


if __name__ == "__main__":
    sys.exit(main())
