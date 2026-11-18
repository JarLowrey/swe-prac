"""Build and check algorithm problems: writes algorithms/<id>/tests.json from cases.py.

    python tools/build_algo.py                  # every problem
    python tools/build_algo.py a01_two_sum ...  # some problems
    python tools/build_algo.py --check          # verify tests.json is current; write nothing

For each problem it:
1. checks the folder has every file and problem.json is valid;
2. computes each case's expected result with the reference solution (solution.py); a case that
   states its own "expect" must agree with the reference;
3. compares the reference with brute() (when cases.py has one) on every case and on
   random_cases();
4. writes tests.json;
5. runs the reference through the real test runner (it must pass every test, inside each test's
   time limit), runs the starter code (it must fail something) and runs the scratch starter;
6. checks the markdown renders without diagram errors.

The format is described in algorithms/README.md.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import random
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from swe_prac import algorithms, config, execution, runner  # noqa: E402
from swe_prac.problems import render_markdown  # noqa: E402

KINDS = {None, "listnode", "listnodes", "tree", "graph"}
RESULT_KINDS = {None, "listnode", "tree", "graph"}
COMPARES = {"exact", "unordered", "unordered_nested", "validator"}
RANDOM_SEED = 20261117
HELPERS_FILE = ROOT / "swe_prac" / "scratch_helpers.py"
GENERATED_NOTE = "by tools/build_algo.py from cases.py and solution.py; do not edit"


class BuildError(Exception):
    pass


def keep_full_speed() -> None:
    """Opt this process out of Windows power throttling (EcoQoS). After a process has been idle
    for a few seconds, for example waiting for the runner, Windows can run it 5 to 15 times
    slower, and the reference's timings become meaningless. Does nothing on other systems."""
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    class ThrottlingState(ctypes.Structure):  # PROCESS_POWER_THROTTLING_STATE
        _fields_ = [(name, wintypes.ULONG) for name in ("Version", "ControlMask", "StateMask")]

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        state = ThrottlingState(1, 1, 0)  # version 1; EXECUTION_SPEED; 0 = never throttle
        process = wintypes.HANDLE(kernel32.GetCurrentProcess())
        # 4 is ProcessPowerThrottling. Windows before 10 lacks the call: then nothing changes.
        kernel32.SetProcessInformation(process, 4, ctypes.byref(state), ctypes.sizeof(state))
    except (AttributeError, OSError):
        pass


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def jsonable(value):
    """Round-trip through JSON: tuples become lists, and anything else unsupported fails."""
    try:
        return json.loads(json.dumps(value))
    except (TypeError, ValueError) as exc:
        raise BuildError(f"not JSON-serialisable: {value!r} ({exc})") from None


def normalize_case(case, where: str) -> dict:
    if isinstance(case, tuple):
        case = {"args": case}
    if not isinstance(case, dict) or not isinstance(case.get("args"), (tuple, list)):
        raise BuildError(
            f"{where}: a case is a tuple of arguments, or a dict with 'args' (a tuple). "
            "Wrap a single argument as (x,)."
        )
    out = {"args": jsonable(list(case["args"]))}
    for key in ("name", "expect", "limit_ms"):
        if key in case:
            out[key] = case[key]
    unknown = set(case) - {"args", "name", "expect", "limit_ms"}
    if unknown:
        raise BuildError(f"{where}: unknown keys {sorted(unknown)}")
    return out


def validate_meta(path: Path) -> dict:
    missing = [n for n in (*algorithms.REQUIRED, "cases.py") if not (path / n).exists()]
    if missing:
        raise BuildError(f"missing files: {', '.join(missing)}")
    meta = json.loads((path / "problem.json").read_text(encoding="utf-8"))
    for key in ("id", "number", "title", "difficulty", "signature", "patterns"):
        if key not in meta:
            raise BuildError(f"problem.json needs {key!r}")
    if meta["id"] != path.name:
        raise BuildError(f"problem.json id {meta['id']!r} must equal the folder name")
    if meta["difficulty"] not in config.ALGO_MINUTES:
        raise BuildError(f"difficulty must be one of {config.ALGO_DIFFICULTIES}")
    if not re.match(r"\s*def\s+\w+\s*\(\s*self\b.*\)\s*(->.*)?:\s*$", meta["signature"]):
        raise BuildError("signature must look like 'def name(self, a: int) -> int:'")
    adapters = meta.get("adapters") or {}
    if set(adapters) - {"args", "result", "check"}:
        raise BuildError("adapters takes 'args', 'result' and 'check'")
    if any(k not in KINDS for k in adapters.get("args", [])):
        raise BuildError(f"adapter kinds are {sorted(k for k in KINDS if k)} or null")
    if adapters.get("result") not in RESULT_KINDS:
        raise BuildError(f"result adapter must be one of {sorted(k for k in RESULT_KINDS if k)}")
    if adapters.get("check", "result") not in ("result", "arg0"):
        raise BuildError("adapters.check is 'result' or 'arg0'")
    compare = meta.get("compare", "exact")
    if compare not in COMPARES:
        raise BuildError(f"compare must be one of {sorted(COMPARES)}")
    if compare == "validator" and not (path / "checker.py").exists():
        raise BuildError("compare 'validator' needs checker.py with check(args, expect, actual)")
    return meta


class Problem:
    """One problem folder being built."""

    def __init__(self, path: Path):
        self.path = path
        self.meta = validate_meta(path)
        self.adapters = self.meta.get("adapters") or {}
        self.arg_kinds = list(self.adapters.get("args") or [])
        self.method = re.match(r"\s*def\s+(\w+)", self.meta["signature"]).group(1)
        tag = path.name
        self.reference = load_module(path / "solution.py", f"_ref_{tag}")
        self.cases = load_module(path / "cases.py", f"_cases_{tag}")
        self.options = {"compare": self.meta.get("compare", "exact"), "normalize": True}
        self.checker = None
        if self.options["compare"] == "validator":
            ns: dict = {}
            source = (path / "checker.py").read_text(encoding="utf-8")
            exec(compile(source, str(path / "checker.py"), "exec"), ns)
            self.checker = ns["check"]

    def run_reference(self, args: list):
        kinds = self.arg_kinds
        adapted = [
            runner.adapt_arg(kinds[i] if i < len(kinds) else None, a, self.reference)
            for i, a in enumerate(copy.deepcopy(args))
        ]
        method = getattr(self.reference.Solution(), self.method)
        timing: dict = {}
        result = runner.call(method, adapted, deep=True, timing=timing)
        ms = timing["ms"]
        if self.adapters.get("check") == "arg0":
            out = runner.adapt_result(kinds[0] if kinds else None, adapted[0])
        else:
            out = runner.adapt_result(self.adapters.get("result"), result)
        return jsonable(runner.plain(out)), ms

    def agree(self, args, expect, actual) -> tuple[bool, str | None]:
        return runner.compare(self.options, copy.deepcopy(args), expect, actual, self.checker)


def build(path: Path, write: bool) -> list[str]:
    """Build one problem. Returns warnings; raises BuildError on a problem."""
    warnings: list[str] = []
    prob = Problem(path)
    shown_src = getattr(prob.cases, "SHOWN", None)
    hidden_src = getattr(prob.cases, "HIDDEN", None)
    if not shown_src or not hidden_src:
        raise BuildError("cases.py needs non-empty SHOWN and HIDDEN lists")

    def expand(cases, prefix: str, default_name: str) -> list[dict]:
        out = []
        for i, raw in enumerate(cases, 1):
            case = normalize_case(raw, f"{prefix}{i}")
            got, ms = prob.run_reference(case["args"])
            if "expect" in case:
                ok, why = prob.agree(case["args"], jsonable(case["expect"]), got)
                if not ok:
                    raise BuildError(
                        f"{prefix}{i} ({case.get('name', '')}): the reference returned {got!r} "
                        f"but the case expects {case['expect']!r}" + (f" ({why})" if why else "")
                    )
                expect = jsonable(case["expect"])
            else:
                expect = got
            limit = case.get("limit_ms")
            # One run can be slow because the machine is busy: time it twice more and keep
            # the fastest before warning.
            for _ in range(2):
                if not limit or ms * 10 <= limit:
                    break
                ms = min(ms, prob.run_reference(case["args"])[1])
            if limit and ms * 10 > limit:
                warnings.append(
                    f"{prefix}{i}: the reference took {ms:.0f} ms; keep it under a tenth of "
                    f"limit_ms={limit} so slower machines pass"
                )
            test = {"id": f"{prefix}{i}", "name": case.get("name") or f"{default_name} {i}"}
            test.update({"args": case["args"], "expect": expect})
            if limit:
                test["limit_ms"] = limit
            out.append(test)
        return out

    shown = expand(shown_src, "s", "Example")
    if any(t.get("limit_ms") for t in shown):
        raise BuildError("shown tests can't have limit_ms; put large inputs in HIDDEN")
    # Time-limited tests go last: a test that's too slow stops the run, and the rest don't run.
    hidden_src = sorted(hidden_src, key=lambda c: isinstance(c, dict) and "limit_ms" in c)
    hidden = expand(hidden_src, "h", "Hidden")

    brute = getattr(prob.cases, "brute", None)
    checked = 0
    if brute is not None:
        rng = random.Random(RANDOM_SEED)
        random_args = [
            jsonable(list(a)) for a in (getattr(prob.cases, "random_cases", lambda r: [])(rng))
        ]
        pool = [(t["id"], t["args"], t["expect"]) for t in shown + hidden if not t.get("limit_ms")]
        for n, args in enumerate(random_args, 1):
            pool.append((f"random #{n}", args, prob.run_reference(args)[0]))
        for label, args, ref_out in pool:
            want = jsonable(runner.plain(brute(*copy.deepcopy(args))))
            ok, why = prob.agree(args, want, ref_out)
            if not ok:
                raise BuildError(
                    f"{label}: reference {ref_out!r} disagrees with brute {want!r} for "
                    f"args {json.dumps(args)[:300]}" + (f" ({why})" if why else "")
                )
            checked += 1
    else:
        warnings.append("no brute(): the reference is not cross-checked")

    # Each time-limited test must reject the slow approach: naive() if cases.py has one (the
    # plausible-but-slow solution), otherwise brute().
    slow_name = "naive" if hasattr(prob.cases, "naive") else "brute"
    if hasattr(prob.cases, slow_name):
        for t in hidden:
            if t.get("limit_ms"):
                fast = slow_finishes(path, slow_name, t["args"], t["limit_ms"])
                if fast is not None:
                    warnings.append(
                        f"{t['id']} ({t['name']}): {slow_name}() finishes in {fast:.0f} ms, "
                        f"inside limit_ms={t['limit_ms']}, so the test doesn't reject it. Make "
                        "the input larger or harder"
                        + ("" if slow_name == "naive" else ", or add naive() if brute() is fast")
                        + "."
                    )

    data = {"shown": shown, "hidden": hidden}
    text = render_tests(data)
    target = path / "tests.json"
    if write:
        target.write_text(text, encoding="utf-8")
    elif not target.exists() or target.read_text(encoding="utf-8") != text:
        raise BuildError("tests.json is out of date: run tools/build_algo.py")

    # The real runner, in a subprocess, exactly as a session runs it.
    problem = algorithms._load(path) if target.exists() else None
    if problem is not None:
        verify_with_runner(problem, warnings)
    check_markdown(path)
    print(
        f"  {path.name}: {len(shown)} shown, {len(hidden)} hidden"
        + (f", {checked} cross-checked against brute()" if brute else "")
    )
    return warnings


SLOW_TIMER = """
import importlib.util, json, sys, threading, time
sys.setrecursionlimit(200_000)
threading.stack_size(64 * 1024 * 1024)
spec = importlib.util.spec_from_file_location("cases", sys.argv[1])
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)
args = json.load(open(sys.argv[2], encoding="utf-8"))
def go():
    t = time.perf_counter()
    getattr(cases, sys.argv[3])(*args)
    print((time.perf_counter() - t) * 1000)
worker = threading.Thread(target=go)
worker.start()
worker.join()
"""


def slow_finishes(path: Path, name: str, args: list, limit_ms: int) -> float | None:
    """The time naive() or brute() takes on a large test, in ms, if it finishes inside the
    limit; else None. Runs in a subprocess so a slow one can be killed."""
    with tempfile.TemporaryDirectory() as tmp:
        args_file = Path(tmp) / "args.json"
        args_file.write_text(json.dumps(args), encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-c", SLOW_TIMER, str(path / "cases.py"), str(args_file), name],
                capture_output=True,
                text=True,
                timeout=1 + limit_ms * 3 / 1000,
            )
        except subprocess.TimeoutExpired:
            return None
    if proc.returncode != 0:
        raise BuildError(f"{name}() fails on a large test: {proc.stderr[-500:]}")
    ms = float(proc.stdout.strip().splitlines()[-1])
    return ms if ms <= limit_ms else None


def verify_with_runner(problem: algorithms.Problem, warnings: list[str]) -> None:
    tests = algorithms.tests(problem, include_hidden=True)
    options = problem.runner_options()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        run = execution.run_tests(
            work / "ref", algorithms.solution_code(problem), "Solution", tests, options
        )
        if run.import_error or run.crashed or run.timed_out or run.stopped:
            why = run.import_error or run.crashed or run.stopped or "timeout"
            raise BuildError(f"the reference fails in the runner: {why}")
        failed = [t["id"] for t in tests if not run.results.get(t["id"], {}).get("passed")]
        if failed:
            first = run.results.get(failed[0], {})
            raise BuildError(
                f"the reference fails {failed} in the runner: {first.get('error')} "
                f"{first.get('steps')}"
            )
        slowest = max((r.get("ms") or 0) for r in run.results.values())
        if slowest > 2000:
            warnings.append(f"the slowest test takes {slowest:.0f} ms in the runner")

        stub = execution.run_tests(
            work / "stub", algorithms.starter_code(problem), "Solution", tests, options
        )
        if stub.import_error:
            raise BuildError(f"the starter code doesn't import: {stub.import_error}")
        if all(r.get("passed") for r in stub.results.values()):
            raise BuildError("the starter code passes every test: the tests check nothing")

        scratch = execution.run_scratch(
            work / "scratch",
            algorithms.solution_code(problem),
            algorithms.scratch_starter(problem),
            {"helpers.py": HELPERS_FILE.read_text(encoding="utf-8")},
        )
        if scratch["exit_code"] != 0:
            raise BuildError(f"the scratch starter fails with the reference: {scratch['stderr']}")


def check_markdown(path: Path) -> None:
    for name in ("statement.md", "hints.md", "explanation.md"):
        text = (path / name).read_text(encoding="utf-8")
        if name == "explanation.md":
            if len(algorithms.SOLUTION_MARKER.findall(text)) != 1:
                raise BuildError("explanation.md needs one empty ```solution block")
            solution = (path / "solution.py").read_text(encoding="utf-8")
            text = algorithms.expand_solution(text, solution)
        html = render_markdown(text)
        m = re.search(r'<div class="diagram-error"><strong>([^<]*)</strong>\s*([^<]*)', html)
        if m:
            raise BuildError(f"{name}: {m.group(1)} {m.group(2).strip()}")


def render_tests(data: dict) -> str:
    """One test per line: readable diffs, compact big inputs."""
    parts = ["{"]
    parts.append(f'"_generated": "{GENERATED_NOTE}",')
    for key in ("shown", "hidden"):
        lines = [json.dumps(t, separators=(",", ":")) for t in data[key]]
        parts.append(f'"{key}": [\n' + ",\n".join(lines) + "\n]" + ("," if key == "shown" else ""))
    parts.append("}")
    return "\n".join(parts) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ids", nargs="*", help="problem folders (default: all)")
    parser.add_argument("--check", action="store_true", help="verify only; write nothing")
    args = parser.parse_args(argv)
    keep_full_speed()
    sys.setrecursionlimit(runner.DEEP_RECURSION_LIMIT)
    threading.stack_size(runner.DEEP_STACK_BYTES)
    root = config.ALGO_DIR
    folders = (
        [root / i for i in args.ids]
        if args.ids
        else sorted(p for p in root.iterdir() if p.is_dir() and (p / "problem.json").exists())
    )
    failures = 0
    numbers: dict[int, str] = {}
    for path in folders:
        try:
            for w in build(path, write=not args.check):
                print(f"  warning: {path.name}: {w}")
            number = json.loads((path / "problem.json").read_text(encoding="utf-8"))["number"]
            if number in numbers:
                raise BuildError(f"number {number} is also used by {numbers[number]}")
            numbers[number] = path.name
        except BuildError as exc:
            failures += 1
            print(f"FAILED {path.name}: {exc}")
        except Exception as exc:  # an exception in a reference, brute() or cases.py
            failures += 1
            print(f"FAILED {path.name}: {type(exc).__name__}: {exc}")
    print(f"{len(folders) - failures} of {len(folders)} problems OK")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
