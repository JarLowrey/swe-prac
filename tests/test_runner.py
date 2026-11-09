from __future__ import annotations

from swe_prac import config, execution
from swe_prac.runner import decode, matches


def _tests(*steps_lists):
    return [
        {"id": f"T{i}", "level": 1, "visibility": "shown", "name": f"t{i}", "steps": steps}
        for i, steps in enumerate(steps_lists)
    ]


def test_matches_is_type_strict():
    assert matches(True, True)
    assert not matches(True, 1)
    assert not matches(1, True)
    assert matches(None, None)
    assert not matches(None, 0)
    assert not matches(0, None)
    assert matches(10, 10.0)
    assert not matches("1", 1)
    assert not matches(False, None)


def test_decode_tuples():
    assert decode([{"__tuple__": ["A", 2]}, {"x": 1}]) == [("A", 2), {"x": 1}]


def test_pass_fail_and_stops_at_first_failure(tmp_path):
    code = "class C:\n    def f(self, ts, x):\n        print('saw', x)\n        return x * 2\n"
    tests = _tests(
        [{"call": "f", "args": [1, 2], "expect": 4}],
        [{"call": "f", "args": [1, 2], "expect": 5}, {"call": "f", "args": [2, 3], "expect": 6}],
    )
    run = execution.run_tests(tmp_path, code, "C", tests)
    assert run.import_error is None
    assert run.results["T0"]["passed"] is True
    assert "saw 2" in run.results["T0"]["stdout"]
    bad = run.results["T1"]
    assert bad["passed"] is False
    assert bad["failed_step"] == 0
    assert len(bad["steps"]) == 1  # second step never ran
    assert bad["steps"][0]["expect"] == "5" and bad["steps"][0]["actual"] == "4"


def test_exception_traceback_shows_only_user_frames(tmp_path):
    code = "class C:\n    def f(self, ts):\n        return {}['missing']\n"
    run = execution.run_tests(
        tmp_path, code, "C", _tests([{"call": "f", "args": [1], "expect": 1}])
    )
    result = run.results["T0"]
    assert not result["passed"]
    assert "KeyError" in result["error"]
    assert 'File "solution.py", line 3, in f' in result["error"]
    assert "runner.py" not in result["error"]
    assert str(tmp_path) not in result["error"]  # no absolute session paths


def test_unchecked_steps_and_missing_method(tmp_path):
    code = "class C:\n    def f(self, ts):\n        return 'anything'\n"
    tests = _tests([{"call": "f", "args": [1]}, {"call": "g", "args": [2], "expect": 1}])
    result = execution.run_tests(tmp_path, code, "C", tests).results["T0"]
    assert result["steps"][0]["ok"] is True and result["steps"][0]["checked"] is False
    assert "`g` is not defined" in result["error"]


def test_syntax_error_and_missing_class(tmp_path):
    run = execution.run_tests(tmp_path, "class C:\n  def f(:\n", "C", _tests([]))
    assert run.import_error and "SyntaxError" in run.import_error
    run = execution.run_tests(tmp_path, "x = 1\n", "C", _tests([]))
    assert "class named `C`" in run.import_error


def test_tuple_args_reach_user_code(tmp_path):
    code = (
        "class C:\n"
        "    def f(self, ts, lines):\n"
        "        return all(type(x) is tuple for x in lines)\n"
    )
    tests = _tests([{"call": "f", "args": [1, [{"__tuple__": ["A", 1]}]], "expect": True}])
    assert execution.run_tests(tmp_path, code, "C", tests).results["T0"]["passed"]


def test_infinite_loop_times_out_with_partial_results(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUN_TIMEOUT_SECONDS", 3)
    code = (
        "class C:\n    def ok(self, ts):\n        return 1\n"
        "    def spin(self, ts):\n        while True:\n            pass\n"
    )
    tests = _tests(
        [{"call": "ok", "args": [1], "expect": 1}],
        [{"call": "spin", "args": [1], "expect": 1}],
        [{"call": "ok", "args": [1], "expect": 1}],
    )
    run = execution.run_tests(tmp_path, code, "C", tests)
    assert run.timed_out
    assert run.results["T0"]["passed"]
    assert not run.results["T1"]["passed"] and "Timed out" in run.results["T1"]["error"]
    assert "T2" not in run.results  # never ran


def test_scratch_imports_solution(tmp_path):
    out = execution.run_scratch(
        tmp_path, "class C:\n    X = 41\n", "from solution import *\nprint(C.X + 1, 'é')\n"
    )
    assert out["exit_code"] == 0
    assert out["stdout"].strip() == "42 é"


def test_lint_and_format():
    lint = execution.lint("import os\nx=1\n")
    codes = {i["code"] for i in lint["issues"]}
    assert "F401" in codes
    formatted = execution.format_code("x=[1,2 ,3]\n")
    assert formatted["code"] == "x = [1, 2, 3]\n"
    assert execution.format_code("def (:\n")["error"]
