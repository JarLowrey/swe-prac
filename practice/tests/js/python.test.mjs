// python.js: Run, Submit and Run scratch in a fresh worker each, with the page's time limits.
// These go through the real worker script (py-worker.js) on harness.mjs's Worker stand-in.
import assert from "node:assert/strict";
import { after, before, describe, test } from "node:test";

import { python } from "./harness.mjs";

let py;
before(async () => {
  py = await python();
});
after(() => py.coolDown());

const one = (id, call, args, expect, extra = {}) => ({
  id, name: id, visibility: "shown", steps: [{ call, args, expect }], ...extra,
});

const DEEP = `from functools import cache


class Solution:
    def plain(self, n):
        def go(k):
            return 0 if k == 0 else 1 + go(k - 1)
        return go(n)

    def cached(self, n):
        @cache
        def go(k):
            return 0 if k == 0 else 1 + go(k - 1)
        return go(n)

    def through_max(self, n):
        def go(k):
            return 0 if k == 0 else 1 + max(go(j) for j in (k - 1,))
        return go(n)

    def through_list(self, n):
        def go(k):
            return 0 if k == 0 else 1 + len(list(go(j) for j in (k - 1,)))
        return go(n)
`;

describe("tests", () => {
  test("a passing and a failing test, with the step details the page shows", async () => {
    const code = "class S:\n    def add(self, a, b):\n        print('adding', a, b)\n        return a + b\n";
    const run = await py.runTests({
      code,
      className: "S",
      tests: [one("t1", "add", [1, 2], 3), one("t2", "add", [2, 2], 5)],
    });
    assert.equal(run.import_error, null);
    assert.equal(run.crashed, null);
    assert.equal(run.results.t1.passed, true);
    assert.equal(run.results.t1.stdout, "adding 1 2\n");
    assert.equal(run.results.t2.passed, false);
    assert.deepEqual(run.results.t2.steps[0], {
      call: "add", args: "2, 2", checked: true, expect: "5", actual: "4", ok: false,
    });
    assert.ok(run.ms > 0);
  });

  test("a syntax error is an import error that names solution.py", async () => {
    const run = await py.runTests({ code: "class S:\n    def f(self)\n", className: "S", tests: [one("t1", "f", [], 1)] });
    assert.match(run.import_error, /solution\.py/);
    assert.match(run.import_error, /SyntaxError/);
    assert.doesNotMatch(run.import_error, /\/work\//);
    assert.deepEqual(run.results, {});
  });

  test("a missing class is an import error", async () => {
    const run = await py.runTests({ code: "x = 1\n", className: "S", tests: [one("t1", "f", [], 1)] });
    assert.match(run.import_error, /must define a class named `S`/);
  });

  test("deep recursion works through plain calls, functools.cache and max over a generator", async () => {
    const tests = ["plain", "cached", "through_max"].map((m) => one(m, m, [20000], 20000));
    const run = await py.runTests({ code: DEEP, className: "Solution", tests, options: { deep_recursion: true } });
    assert.equal(run.crashed, null);
    for (const t of tests) assert.ok(run.results[t.id].passed, `${t.id}: ${run.results[t.id].error}`);
  });

  test("recursion through other C code stops Python with an explanation", async () => {
    const run = await py.runTests({
      code: DEEP,
      className: "Solution",
      tests: [one("through_list", "through_list", [150000], 150000)],
      options: { deep_recursion: true },
    });
    assert.match(run.crashed, /Python ran out of stack and stopped/);
    assert.equal(run.results.through_list.passed, false);
    assert.match(run.results.through_list.error, /exited unexpectedly/);
  });

  test("long linked lists are built, checked and dropped without crashing", async () => {
    const n = 50000;
    const values = Array.from({ length: n }, (_, i) => i);
    const code = `class Solution:
    def reverseList(self, head):
        prev = None
        while head:
            head.next, prev, head = prev, head, head.next
        return prev
`;
    const tests = [0, 1, 2].map((i) => one(`t${i}`, "reverseList", [values], [...values].reverse()));
    const run = await py.runTests({
      code,
      className: "Solution",
      tests,
      options: { normalize: true, deep_recursion: true, compare: "exact", adapters: { args: ["listnode"], result: "listnode" } },
    });
    assert.equal(run.crashed, null);
    for (const t of tests) assert.ok(run.results[t.id].passed, run.results[t.id].error);
  });

  test("a call still running at 1.5 times its limit is stopped, and the tests after it don't run", async () => {
    const code = "class S:\n    def f(self, n):\n        while n:\n            pass\n        return n\n";
    const run = await py.runTests({
      code,
      className: "S",
      tests: [one("quick", "f", [0], 0, { limit_ms: 200 }), one("slow", "f", [1], 1, { limit_ms: 200 }), one("next", "f", [0], 0)],
    });
    assert.equal(run.results.quick.passed, true);
    assert.equal(run.results.slow.passed, false);
    assert.equal(run.results.slow.error, "Too slow: stopped after 300 ms; the limit for this test is 200 ms. Look for a faster algorithm.");
    assert.equal(run.stopped, run.results.slow.error);
    assert.equal(run.results.next, undefined);
    assert.ok(run.ms < 3000, `stopped after ${run.ms} ms`);
  });
});

// The two 10-second limits, side by side so they cost 10 seconds between them.
describe("time limits", () => {
  test("a run past 10 s times out and keeps the results so far; so does scratch", async () => {
    const code = "class S:\n    def f(self, n):\n        while n:\n            pass\n        return n\n";
    const [run, scratch] = await Promise.all([
      py.runTests({ code, className: "S", tests: [one("done", "f", [0], 0), one("loops", "f", [1], 1)] }),
      py.runScratch({ code: "", scratch: "print('before', flush=True)\nwhile True:\n    pass\n" }),
    ]);
    assert.equal(run.timed_out, true);
    assert.equal(run.results.done.passed, true);
    assert.match(run.results.loops.error, /^Timed out: the whole run exceeded 10s/);
    assert.ok(run.ms >= 10000 && run.ms < 13000, `${run.ms} ms`);

    assert.equal(scratch.timed_out, true);
    assert.equal(scratch.exit_code, null);
    assert.equal(scratch.stdout, "before\n");
    assert.match(scratch.stderr, /Timed out after 10s\.$/);
  });
});

describe("scratch", () => {
  test("it runs as a program beside solution.py, with stdout, stderr and the exit code", async () => {
    const out = await py.runScratch({
      code: "def twice(x):\n    return 2 * x\n",
      scratch: "import sys\nfrom solution import twice\nprint(twice(21))\nprint('note', file=sys.stderr)\nsys.exit(3)\n",
    });
    assert.deepEqual([out.stdout, out.stderr, out.exit_code, out.timed_out, out.crashed], ["42\n", "note\n", 3, false, false]);
  });

  test("an error prints a traceback with the editor's file names", async () => {
    const out = await py.runScratch({ code: "def boom():\n    raise ValueError('bad')\n", scratch: "from solution import boom\nboom()\n" });
    assert.equal(out.exit_code, 1);
    assert.match(out.stderr, /File "scratch\.py", line 2/);
    assert.match(out.stderr, /File "solution\.py", line 2, in boom/);
    assert.doesNotMatch(out.stderr, /\/work\//);
    assert.match(out.stderr, /ValueError: bad/);
  });

  test("input() reads end of file, as a program with no input does", async () => {
    const out = await py.runScratch({ code: "", scratch: "input()\n" });
    assert.equal(out.exit_code, 1);
    assert.match(out.stderr, /EOFError/);
  });

  test("runaway recursion is a quick RecursionError", async () => {
    const out = await py.runScratch({ code: "", scratch: "def f(n):\n    return f(n + 1)\nf(0)\n" });
    assert.equal(out.exit_code, 1);
    assert.match(out.stderr, /RecursionError/);
    assert.ok(out.ms < 3000, `${out.ms} ms`);
  });

  test("output stops at 50,000 characters", async () => {
    const out = await py.runScratch({ code: "", scratch: "for i in range(100000):\n    print('x' * 9)\n" });
    assert.equal(out.exit_code, 0);
    assert.equal(out.stdout.length, 50000);
  });

  test("each run has a fresh interpreter", async () => {
    await py.runScratch({ code: "", scratch: "import builtins\nbuiltins.left_behind = 1\n" });
    const out = await py.runScratch({ code: "", scratch: "import builtins\nprint(hasattr(builtins, 'left_behind'))\n" });
    assert.equal(out.stdout, "False\n");
  });

  test("the page hears when a run has to wait for Python to load", async () => {
    py.coolDown(); // no spare: this run starts its interpreter from scratch
    const states = [];
    const listen = (e) => states.push(e.detail.state);
    window.addEventListener("swe-python", listen);
    try {
      const out = await py.runScratch({ code: "", scratch: "print('hi')\n" });
      assert.equal(out.stdout, "hi\n");
    } finally {
      window.removeEventListener("swe-python", listen);
    }
    assert.deepEqual(states, ["loading", "running"]);
  });
});
