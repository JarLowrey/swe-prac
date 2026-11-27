"""Compile and verify a problem package.

    python tools/build_problem.py p1_file_store        # one problem
    python tools/build_problem.py --all                # every problem

Reads problems/<pid>/problem.json and
reference/<pid>/{solution.py, tests.txt, gen.py, mutants/*.py}.
Writes problems/<pid>/tests.json and problems/<pid>/stubs.json.

Checks (any failure exits non-zero):
  * problem.json is well-formed; every public reference method is assigned to exactly one level.
  * every test step only calls methods from its own level or earlier, and timestamps
    (the first argument) strictly increase within a test.
  * hand-written expectations agree with the reference solution; `-> ?` and @gen steps are
    filled in from it. Return values must be None/bool/int/float/str.
  * the real subprocess runner passes the reference on every test.
  * every mutant in reference/<pid>/mutants fails at least one hidden test.
  * every level has at least one shown and one hidden test.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import random
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import dsl  # noqa: E402

from swe_prac.execution import format_code  # noqa: E402
from swe_prac.runner import matches  # noqa: E402


def _format_methods(methods: str) -> str:
    """Format indented method stubs with the same ruff config as the app's Format button."""
    result = format_code(f"class _Stub:\n{methods}")
    if result["error"]:
        raise BuildError(f"generated stubs do not parse: {result['error']}")
    return result["code"].split("\n", 1)[1]


RUNNER = ROOT / "swe_prac" / "runner.py"
ALLOWED_RETURN = (type(None), bool, int, float, str)


class BuildError(Exception):
    pass


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def encode(value):
    if isinstance(value, tuple):
        return {"__tuple__": [encode(v) for v in value]}
    if isinstance(value, list):
        return [encode(v) for v in value]
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    return value


def method_levels(problem: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for lvl in problem["levels"]:
        for m in lvl["methods"]:
            if m in out:
                raise BuildError(f"method {m} listed in two levels")
            out[m] = lvl["level"]
    return out


def check_problem_json(problem: dict, pid: str) -> None:
    for key in ("id", "number", "title", "summary", "class_name", "levels"):
        if key not in problem:
            raise BuildError(f"problem.json missing {key!r}")
    if problem["id"] != pid:
        raise BuildError(f"problem.json id {problem['id']!r} != folder {pid!r}")
    if [lvl["level"] for lvl in problem["levels"]] != [1, 2, 3, 4]:
        raise BuildError("problem.json must define levels 1..4 in order")
    for lvl in problem["levels"]:
        if not lvl.get("title"):
            raise BuildError(f"level {lvl['level']} needs a title")


def make_stubs(solution_src: str, class_name: str, levels: dict[str, int]) -> dict[str, str]:
    tree = ast.parse(solution_src)
    cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name), None)
    if cls is None:
        raise BuildError(f"reference solution has no class {class_name}")
    public = {}
    for node in cls.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            public[node.name] = node
    missing = set(levels) - set(public)
    extra = set(public) - set(levels)
    if missing:
        raise BuildError(f"reference is missing methods: {sorted(missing)}")
    if extra:
        raise BuildError(f"reference has public methods not in problem.json: {sorted(extra)}")
    stubs = {"init": "    def __init__(self) -> None:\n        pass\n"}
    for level in (1, 2, 3, 4):
        chunks = []
        for name, node in public.items():
            if levels[name] != level:
                continue
            sig = f"    def {name}({ast.unparse(node.args)})"
            if node.returns is not None:
                sig += f" -> {ast.unparse(node.returns)}"
            doc = ast.get_docstring(node)
            body = ""
            if doc:
                first = doc.strip().splitlines()[0]
                body += f'        """{first}"""\n'
            body += "        raise NotImplementedError\n"
            chunks.append(f"{sig}:\n{body}")
        stubs[str(level)] = _format_methods("\n".join(chunks))
    return stubs


def expand_generated(block: dsl.TestBlock, gen_module) -> None:
    if block.gen is None:
        return
    if gen_module is None:
        raise BuildError(f"test {block.name!r} uses @gen but reference/<pid>/gen.py is missing")
    params = dict(block.gen)
    lines = gen_module.generate(
        level=block.level, rng=random.Random(params.pop("seed", 0)), **params
    )
    for i, line in enumerate(lines):
        step = dsl.parse_step(line, block.line)
        if step.expect is dsl.UNCHECKED:
            step.expect = dsl.GOLDEN
        step.line = block.line
        block.steps.append(step)
        if i > 100_000:
            raise BuildError("generator produced too many steps")


def compile_tests(pid: str, problem: dict, solution_path: Path) -> list[dict]:
    ref_dir = ROOT / "reference" / pid
    blocks = dsl.parse_tests((ref_dir / "tests.txt").read_text(encoding="utf-8"))
    gen_path = ref_dir / "gen.py"
    gen_module = load_module(gen_path, f"gen_{pid}") if gen_path.exists() else None
    ref_cls = getattr(load_module(solution_path, f"ref_{pid}"), problem["class_name"])
    levels = method_levels(problem)

    compiled = []
    counters: Counter = Counter()
    for block in blocks:
        expand_generated(block, gen_module)
        where = f"test '{block.name}' (line {block.line})"
        if not block.steps:
            raise BuildError(f"{where} has no steps")
        last_ts = None
        for step in block.steps:
            if step.call not in levels:
                raise BuildError(f"{where}: unknown method {step.call!r} (line {step.line})")
            if levels[step.call] > block.level:
                raise BuildError(
                    f"{where}: L{block.level} test calls L{levels[step.call]} method "
                    f"{step.call!r} (line {step.line})"
                )
            ts = step.args[0] if step.args else None
            if not isinstance(ts, int) or isinstance(ts, bool):
                raise BuildError(
                    f"{where}: first argument must be an int timestamp (line {step.line})"
                )
            if last_ts is not None and ts <= last_ts:
                raise BuildError(f"{where}: timestamp {ts} does not increase (line {step.line})")
            last_ts = ts

        obj = ref_cls()
        steps_json = []
        for step in block.steps:
            try:
                actual = getattr(obj, step.call)(*step.args)
            except Exception as exc:
                raise BuildError(
                    f"{where}: reference raised {type(exc).__name__}: {exc} on "
                    f"{dsl.format_step(step)} (line {step.line})"
                ) from exc
            if not isinstance(actual, ALLOWED_RETURN):
                raise BuildError(
                    f"{where}: reference returned {type(actual).__name__} (line {step.line})"
                )
            entry = {"call": step.call, "args": encode(step.args)}
            if step.expect is dsl.GOLDEN:
                entry["expect"] = actual
            elif step.expect is not dsl.UNCHECKED:
                if not matches(step.expect, actual):
                    raise BuildError(
                        f"{where}: expected {step.expect!r} but reference returned {actual!r} "
                        f"for {dsl.format_step(step)} (line {step.line})"
                    )
                entry["expect"] = step.expect
            steps_json.append(entry)

        key = (block.level, block.visibility)
        counters[key] += 1
        tag = "S" if block.visibility == "shown" else "H"
        compiled.append(
            {
                "id": f"L{block.level}-{tag}{counters[key]}",
                "level": block.level,
                "visibility": block.visibility,
                "name": block.name,
                "steps": steps_json,
            }
        )

    for level in (1, 2, 3, 4):
        if not counters[(level, "shown")] or not counters[(level, "hidden")]:
            raise BuildError(f"level {level} needs at least one shown and one hidden test")
    compiled.sort(key=lambda t: (t["level"], t["visibility"] != "shown"))
    return compiled


def run_runner(solution: Path, class_name: str, tests_json: Path) -> dict[str, bool]:
    with tempfile.TemporaryDirectory() as tmp:
        results = Path(tmp) / "results.jsonl"
        proc = subprocess.run(
            [
                sys.executable,
                "-I",
                str(RUNNER),
                str(solution),
                class_name,
                str(tests_json),
                str(results),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            raise BuildError(f"runner crashed: {proc.stderr}")
        outcome = {}
        for line in results.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event["event"] == "import_error":
                raise BuildError(f"{solution.name} failed to import: {event['error']}")
            if event["event"] == "end":
                outcome[event["id"]] = event["passed"]
        return outcome


def build(pid: str) -> None:
    pdir = ROOT / "problems" / pid
    ref_dir = ROOT / "reference" / pid
    problem = json.loads((pdir / "problem.json").read_text(encoding="utf-8"))
    check_problem_json(problem, pid)
    for level in (1, 2, 3, 4):
        if not (pdir / "statement" / f"level{level}.md").exists():
            raise BuildError(f"missing statement/level{level}.md")
    for name in ("hints.md", "analysis.md"):
        if not (pdir / "review" / name).exists():
            raise BuildError(f"missing review/{name}")

    solution = ref_dir / "solution.py"
    stubs = make_stubs(
        solution.read_text(encoding="utf-8"), problem["class_name"], method_levels(problem)
    )
    tests = compile_tests(pid, problem, solution)

    tests_json = pdir / "tests.json"
    tests_json.write_text(json.dumps({"tests": tests}, indent=1), encoding="utf-8")
    (pdir / "stubs.json").write_text(json.dumps(stubs, indent=1), encoding="utf-8")

    outcome = run_runner(solution, problem["class_name"], tests_json)
    failed = [tid for tid, ok in outcome.items() if not ok]
    if failed or len(outcome) != len(tests):
        raise BuildError(f"reference fails its own tests through the runner: {failed}")

    by_id = {t["id"]: t for t in tests}
    print(f"[{pid}] tests per level (shown/hidden, steps):")
    for level in (1, 2, 3, 4):
        lv = [t for t in tests if t["level"] == level]
        shown = sum(t["visibility"] == "shown" for t in lv)
        hidden = len(lv) - shown
        steps = sum(len(t["steps"]) for t in lv)
        print(f"  L{level}: {shown} shown, {hidden} hidden, {steps} steps")

    mutants = sorted((ref_dir / "mutants").glob("*.py")) if (ref_dir / "mutants").exists() else []
    if not mutants:
        print("  WARNING: no mutants in reference/<pid>/mutants")
    for mutant in mutants:
        outcome = run_runner(mutant, problem["class_name"], tests_json)
        caught = [tid for tid, ok in outcome.items() if not ok]
        hidden_caught = [tid for tid in caught if by_id[tid]["visibility"] == "hidden"]
        shown_caught = [tid for tid in caught if by_id[tid]["visibility"] == "shown"]
        if not hidden_caught:
            raise BuildError(
                f"mutant {mutant.name} is not caught by any hidden test (shown: {shown_caught})"
            )
        print(
            f"  mutant {mutant.name}: caught by {len(shown_caught)} shown, "
            f"{len(hidden_caught)} hidden -> {hidden_caught[:6]}"
        )
    print(f"[{pid}] OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pid", nargs="?")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    pids = (
        sorted(p.name for p in (ROOT / "problems").iterdir() if (p / "problem.json").exists())
        if args.all
        else [args.pid]
    )
    status = 0
    for pid in pids:
        try:
            build(pid)
        except (BuildError, dsl.DSLError) as exc:
            print(f"[{pid}] BUILD FAILED: {exc}")
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
