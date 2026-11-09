"""Standalone test harness, executed in a fresh subprocess for every Run/Submit.

Usage: python -I runner.py <solution.py> <ClassName> <tests.json> <results.jsonl>

It imports the solution file, then runs each test on a fresh instance of the class.
Results are appended to the results file as JSON lines and flushed after each event,
so the parent process can recover partial results if this process is killed on timeout.

This file must stay self-contained (stdlib only, no package imports): it runs with -I.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import time
import traceback

MAX_STDOUT_CHARS = 20_000
MAX_REPR_CHARS = 2_000


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
        tests = decode(json.load(fh))["tests"]
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

    for test in tests:
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
                call, args = step["call"], step["args"]
                record = {
                    "call": call,
                    "args": ", ".join(short_repr(a) for a in args),
                    "checked": "expect" in step,
                }
                if "expect" in step:
                    record["expect"] = short_repr(step["expect"])
                method = getattr(obj, call, None)
                if not callable(method):
                    record["ok"] = False
                    record["actual"] = "<method not defined>"
                    steps_out.append(record)
                    passed, failed_step = False, index
                    error = f"Method `{call}` is not defined on `{class_name}`."
                    break
                try:
                    actual = method(*args)
                except BaseException as exc:
                    record["ok"] = False
                    record["actual"] = f"<raised {type(exc).__name__}>"
                    steps_out.append(record)
                    passed, failed_step = False, index
                    error = user_traceback(exc, solution_path)
                    break
                record["actual"] = short_repr(actual)
                record["ok"] = matches(step["expect"], actual) if "expect" in step else True
                steps_out.append(record)
                if not record["ok"]:
                    passed, failed_step = False, index
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
    emit({"event": "done"})
    out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
