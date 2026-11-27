// Every reference solution passes every one of its tests, hidden ones included, in the browser's
// Python (Pyodide), within the time limits the page enforces; every starter fails cleanly.
// The build checks the same natively (tools/build_problem.py, tools/build_algo.py), but code
// can behave differently here: no threads, and a small stack for recursion through C code.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { after, before, describe, test } from "node:test";

import { REPO, data, inlinePython, python, readSiteJson } from "./harness.mjs";

const LIMIT_GRACE = 1.5; // python.js stops a call at 1.5 times its limit_ms

let run; // one interpreter for the sweep: each job reloads solution.py

before(async () => {
  run = await inlinePython();
});

function endEvents(events) {
  const ends = events.filter((e) => e.event === "end");
  return { ends, importError: events.find((e) => e.event === "import_error") ?? null };
}

function checkAllPass(tests, events) {
  const { ends, importError } = endEvents(events);
  assert.equal(importError, null);
  assert.deepEqual(ends.map((e) => e.id), tests.map((t) => t.id));
  for (const end of ends) {
    assert.ok(end.passed, `${end.id}: ${end.error ?? JSON.stringify(end.steps.find((s) => !s.ok))}`);
  }
  for (const t of tests.filter((x) => x.limit_ms)) {
    const end = ends.find((e) => e.id === t.id);
    assert.ok(end.ms <= t.limit_ms * LIMIT_GRACE, `${t.id} took ${end.ms} ms; the limit is ${t.limit_ms} ms`);
  }
}

describe("coding problems", () => {
  for (const item of data.problems) {
    const id = item.problem.id;

    test(`${id}: the reference passes every test of every level`, async () => {
      const file = await readSiteJson(`tests/coding/${id}.json`);
      const events = run({ kind: "tests", code: item.reference_code, className: file.class_name, tests: file.tests });
      checkAllPass(file.tests, events);
    });

    test(`${id}: the starter fails with NotImplementedError`, async () => {
      const file = await readSiteJson(`tests/coding/${id}.json`);
      const tests = file.tests.filter((t) => t.level === 1 && t.visibility === "shown");
      const { ends, importError } = endEvents(run({ kind: "tests", code: item.starter_code, className: file.class_name, tests }));
      assert.equal(importError, null);
      assert.equal(ends.length, tests.length);
      for (const end of ends) {
        assert.equal(end.passed, false);
        assert.match(end.error, /NotImplementedError/);
      }
    });
  }
});

describe("algorithm problems", () => {
  for (const item of data.algo.problems) {
    const id = item.problem.id;

    test(`${id}: the reference passes every test in time`, async () => {
      const file = await readSiteJson(`tests/algo/${id}.json`);
      const reference = readFileSync(join(REPO, "algorithms", id, "solution.py"), "utf8");
      const events = run({ kind: "tests", code: reference, className: file.class_name, tests: file.tests, options: file.options });
      checkAllPass(file.tests, events);
    });

    test(`${id}: the starter runs and fails`, async () => {
      const file = await readSiteJson(`tests/algo/${id}.json`);
      const tests = file.tests.filter((t) => t.visibility === "shown");
      const { ends, importError } = endEvents(run({ kind: "tests", code: item.starter_code, className: file.class_name, tests, options: file.options }));
      assert.equal(importError, null);
      assert.equal(ends.length, tests.length);
      // Some examples can pass (a stub's None is the answer for an empty tree), not all of them.
      assert.ok(!ends.every((e) => e.passed));
    });
  }
});

// Scratch runs each get a fresh worker, as on the page (the script imports solution.py itself).
describe("scratch examples", () => {
  let py;
  before(async () => {
    py = await python();
  });

  for (const item of data.problems) {
    test(`${item.problem.id}: the example passes the reference and fails the starter`, async () => {
      const ok = await py.runScratch({ code: item.reference_code, scratch: item.scratch_starter });
      assert.equal(ok.exit_code, 0, ok.stdout + ok.stderr);
      assert.match(ok.stdout, /test_example/);
      assert.match(ok.stdout, /\nOK\n/);

      const starter = await py.runScratch({ code: item.starter_code, scratch: item.scratch_starter });
      assert.notEqual(starter.exit_code, 0);
      assert.match(starter.stdout + starter.stderr, /NotImplementedError/);
    });
  }

  test("an algorithm's scratch.py runs against the reference with helpers.py beside it", async () => {
    const item = data.algo.problems.find((p) => p.scratch_starter.includes("from helpers import"));
    const id = item.problem.id;
    const reference = readFileSync(join(REPO, "algorithms", id, "solution.py"), "utf8");
    const helpers = readFileSync(join(REPO, "swe_prac", "scratch_helpers.py"), "utf8");
    const out = await py.runScratch({ code: reference, scratch: item.scratch_starter, files: { "helpers.py": helpers } });
    assert.equal(out.exit_code, 0, out.stdout + out.stderr);
    // The starter prints the result with the expected value in a comment below it.
    const expected = item.scratch_starter.match(/^# expected: (.*)$/m)[1];
    assert.equal(out.stdout.trim(), expected);
  });

  after(() => py?.coolDown());
});
