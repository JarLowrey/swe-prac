"""Running user code in fresh subprocesses: tests, scratch scripts, lint and format."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import config

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def _child_env() -> dict[str, str]:
    # User code runs with -I/-E, which ignore PYTHON* variables; strip them anyway so
    # nothing from the app's environment leaks in (ruff runs without those flags).
    return {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}


@dataclass
class TestRun:
    import_error: str | None = None
    import_stdout: str = ""
    timed_out: bool = False
    crashed: str | None = None
    stopped: str | None = None  # a test ran past its time limit; later tests didn't run
    results: dict[str, dict] = field(default_factory=dict)  # test id -> end event
    ms: float = 0.0


def run_tests(
    workdir: Path, code: str, class_name: str, tests: list[dict], options: dict | None = None
) -> TestRun:
    """Run `tests` against `code` in a fresh process. Missing results mean not run.

    `options` (adapters, compare mode...) are documented at the top of runner.py.
    """
    workdir.mkdir(parents=True, exist_ok=True)
    solution = workdir / "solution.py"
    solution.write_text(code, encoding="utf-8")
    tests_file = workdir / "tests_run.json"
    payload = {"tests": tests, **({"options": options} if options else {})}
    tests_file.write_text(json.dumps(payload), encoding="utf-8")
    results_file = workdir / "results.jsonl"
    results_file.write_text("", encoding="utf-8")

    run = TestRun()
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            [
                config.PYTHON,
                "-I",
                "-B",
                "-X",
                "utf8",
                str(config.RUNNER_PATH),
                str(solution.resolve()),
                class_name,
                str(tests_file),
                str(results_file),
            ],
            cwd=workdir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=config.RUN_TIMEOUT_SECONDS,
            env=_child_env(),
            creationflags=CREATE_NO_WINDOW,
        )
        if proc.returncode != 0:
            run.crashed = (proc.stderr or proc.stdout or f"exit code {proc.returncode}")[-4000:]
    except subprocess.TimeoutExpired:
        run.timed_out = True
    run.ms = round((time.perf_counter() - started) * 1000, 1)

    in_progress = None
    for line in results_file.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("event")
        if kind == "import_error":
            run.import_error = event["error"]
            run.import_stdout = event.get("stdout", "")
        elif kind == "start":
            in_progress = event["id"]
        elif kind == "end":
            run.results[event["id"]] = event
            in_progress = None
        elif kind == "stopped":
            run.stopped = event["reason"]
    if in_progress is not None:
        reason = (
            f"Timed out: the whole run exceeded {config.RUN_TIMEOUT_SECONDS}s "
            "(infinite loop or very slow code?)"
            if run.timed_out
            else "The test process exited unexpectedly during this test."
        )
        run.results[in_progress] = {
            "id": in_progress,
            "passed": False,
            "steps": [],
            "failed_step": None,
            "error": reason,
            "stdout": "",
            "ms": None,
            "timed_out": run.timed_out,
        }
    return run


def run_scratch(
    workdir: Path, code: str, scratch: str, extra_files: dict[str, str] | None = None
) -> dict:
    """Run the scratch script with the user's solution importable as `solution`.

    `extra_files` ({name: text}) are written next to it first, e.g. helpers.py.
    """
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "solution.py").write_text(code, encoding="utf-8")
    for name, text in (extra_files or {}).items():
        (workdir / name).write_text(text, encoding="utf-8")
    script = workdir / "scratch.py"
    script.write_text(scratch, encoding="utf-8")
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            # -B: never reuse stale bytecode for a just-edited solution.py.
            # -X utf8: non-ASCII output prints instead of crashing on Windows.
            [config.PYTHON, "-E", "-s", "-B", "-X", "utf8", str(script.resolve())],
            cwd=workdir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=config.SCRATCH_TIMEOUT_SECONDS,
            env=_child_env(),
            creationflags=CREATE_NO_WINDOW,
        )
        out = {
            "stdout": proc.stdout[: config.MAX_SCRATCH_OUTPUT],
            "stderr": proc.stderr[: config.MAX_SCRATCH_OUTPUT],
            "exit_code": proc.returncode,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:

        def _text(b):
            return b.decode("utf-8", "replace") if isinstance(b, bytes) else (b or "")

        out = {
            "stdout": _text(exc.stdout)[: config.MAX_SCRATCH_OUTPUT],
            "stderr": _text(exc.stderr)[: config.MAX_SCRATCH_OUTPUT]
            + f"\nTimed out after {config.SCRATCH_TIMEOUT_SECONDS}s.",
            "exit_code": None,
            "timed_out": True,
        }
    out["ms"] = round((time.perf_counter() - started) * 1000, 1)
    return out


def _ruff(
    args: list[str], code: str, ruff_config: Path | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            config.PYTHON,
            "-m",
            "ruff",
            *args,
            "--config",
            str(ruff_config or config.USER_RUFF_CONFIG),
            "--stdin-filename",
            "solution.py",
            "-",
        ],
        input=code,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=_child_env(),
        creationflags=CREATE_NO_WINDOW,
    )


def lint(code: str, ruff_config: Path | None = None) -> dict:
    """ruff issues in `code`; `ruff_config` defaults to the coding track's user_ruff.toml."""
    proc = _ruff(["check", "--output-format", "json", "--no-fix"], code, ruff_config)
    try:
        items = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return {"issues": [], "error": (proc.stderr or proc.stdout).strip()[-2000:]}
    issues = [
        {
            "code": item.get("code") or "syntax",
            "message": item["message"],
            "row": item["location"]["row"],
            "col": item["location"]["column"],
            "end_row": item["end_location"]["row"],
            "end_col": item["end_location"]["column"],
            "fixable": item.get("fix") is not None,
            "url": item.get("url"),
        }
        for item in items
    ]
    issues.sort(key=lambda i: (i["row"], i["col"]))
    return {"issues": issues, "error": None}


def format_code(code: str) -> dict:
    proc = _ruff(["format"], code)
    if proc.returncode != 0:
        return {"code": None, "error": (proc.stderr or "ruff format failed").strip()[-2000:]}
    return {"code": proc.stdout, "error": None}
