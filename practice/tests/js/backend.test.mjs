// backend.js: sessions, timers, scoring, history and its export, against the real data.json,
// with Python and ruff replaced by fakes that answer as told.
import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { data, importSite, readSiteJson, readSiteText } from "./harness.mjs";

const { createBackend } = await importSite("backend.js");

const CODING = data.problems[0].problem.id;
const OTHER = data.problems[1].problem.id;
const ALGO = data.algo.problems[0].problem.id;
const DESIGN = data.design.questions[0].question.id;
const LIMIT = data.time_limit;

function memoryStorage() {
  return { text: null, get() { return this.text; }, set(text) { this.text = text; } };
}

// Answers runTests() with every test passing unless verdict(test) says otherwise: false, or an
// error message. hold() makes runs wait until the returned release() is called.
function fakePython() {
  const py = {
    calls: [],
    verdict: () => true,
    gate: null,
    hold() {
      let release;
      py.gate = new Promise((resolve) => { release = resolve; });
      return () => { py.gate = null; release(); };
    },
    async runTests(job) {
      py.calls.push(job);
      if (py.gate) await py.gate;
      const results = {};
      for (const t of job.tests) {
        const v = py.verdict(t);
        const passed = v === true;
        const error = passed ? null : typeof v === "string" ? v : "AssertionError";
        results[t.id] = { id: t.id, passed, steps: [], failed_step: passed ? null : 0, error, stdout: "", ms: 1 };
      }
      return { import_error: null, import_stdout: "", timed_out: false, crashed: null, stopped: null, results, ms: 5 };
    },
    async runScratch(job) {
      py.calls.push(job);
      return { stdout: "scratch ran\n", stderr: "", exit_code: 0, timed_out: false, crashed: false, ms: 3 };
    },
  };
  return py;
}

// A compiled language (compiled.js): runTests reports the build's warnings as its lint.
function fakeCompiled() {
  const c = {
    calls: [],
    async runTests(job) {
      c.calls.push(job);
      const results = {};
      for (const t of job.tests) results[t.id] = { id: t.id, passed: true, steps: [], failed_step: null, error: null, stdout: "", ms: 1 };
      return {
        import_error: null, import_stdout: "", timed_out: false, crashed: null, stopped: null, results, ms: 5,
        compile_error: false, lint: { issues: [{ code: "warning", message: "unused", row: 2, col: 1, end_row: 2, end_col: 2, fixable: false }], error: null },
      };
    },
    async runScratch(job) {
      c.calls.push(job);
      return { stdout: "compiled scratch\n", stderr: "", exit_code: 0, timed_out: false, crashed: false, ms: 3 };
    },
    async lint(job) {
      c.calls.push(job);
      return { issues: [], error: null };
    },
  };
  return c;
}

function fakeRuff() {
  const ruff = {
    calls: [],
    broken: false,
    async lint(code, settings) {
      ruff.calls.push({ code, settings });
      if (ruff.broken) throw new Error("no wasm");
      return { issues: code.includes("import os") ? [{ code: "F401", message: "unused", row: 1, col: 1, end_row: 1, end_col: 10, fixable: true }] : [], error: null };
    },
    async format(code, settings) {
      ruff.calls.push({ code, settings });
      if (ruff.broken) throw new Error("no wasm");
      return { code: `${code.trim()}\n`, error: null };
    },
  };
  return ruff;
}

// One browser tab's backend. Tabs given the same storage share their history.
function tab({ storage = memoryStorage(), clock = { now: 1_000_000 } } = {}) {
  const python = fakePython();
  const java = fakeCompiled();
  const cpp = fakeCompiled();
  const ruff = fakeRuff();
  const storageErrors = [];
  const backend = createBackend({
    fetchJson: readSiteJson,
    fetchText: readSiteText,
    storage,
    python,
    java,
    cpp,
    ruff,
    clock: () => clock.now,
    random: () => 0,
    onStorageError: (message) => storageErrors.push(message),
  });
  return {
    api: (method, path, body) => backend.handle(method, path, body),
    python, java, cpp, ruff, storage, clock, storageErrors,
    advance(seconds) { clock.now += seconds; },
  };
}

const testsFile = (track, id) => readSiteJson(`tests/${track}/${id}.json`);

describe("coding sessions", () => {
  test("a submit that passes every test of the current level completes it and unlocks the next", async () => {
    const t = tab();
    const file = await testsFile("coding", CODING);
    const item = data.problems[0];
    let s = await t.api("POST", "/api/sessions", { problem_id: CODING, mode: "strict" });
    assert.equal(s.current_level, 1);
    assert.equal(s.levels.length, 1); // later levels stay hidden
    assert.equal(s.code, item.starter_code);
    assert.equal(s.tests_source, item.tests_source["1"]);

    t.advance(100);
    const run = await t.api("POST", `/api/sessions/${s.id}/run`, { code: "mine" });
    const shown1 = file.tests.filter((x) => x.level === 1 && x.visibility === "shown");
    assert.deepEqual(t.python.calls[0].tests.map((x) => x.id), shown1.map((x) => x.id));
    assert.equal(t.python.calls[0].code, "mine");
    assert.equal(t.python.calls[0].className, file.class_name);
    assert.equal(run.unlocked, null);
    assert.equal(run.shown.length, shown1.length);

    for (let level = 1; level <= 4; level++) {
      t.advance(600);
      const res = await t.api("POST", `/api/sessions/${s.id}/submit`, { code: "mine" });
      const at = file.tests.filter((x) => x.level <= level);
      assert.deepEqual(t.python.calls.at(-1).tests.map((x) => x.id), at.map((x) => x.id));
      assert.equal(res.all_passed, true);
      assert.deepEqual(res.unlocked, { completed: level, new_level: level + 1 });
      const counts = res.breakdown[String(level)];
      assert.equal(counts.hidden_total, at.filter((x) => x.level === level && x.visibility === "hidden").length);
      assert.equal(counts.hidden_passed, counts.hidden_total);
      // Hidden tests: counts only, never their names.
      const text = JSON.stringify(res);
      for (const hidden of at.filter((x) => x.visibility === "hidden" && x.name.length >= 12)) {
        assert.ok(!text.includes(hidden.name), hidden.name);
      }
      s = res.session;
      assert.equal(s.levels.length, Math.min(level + 1, 4));
    }
    assert.equal(s.all_levels_done, true);
    assert.equal(s.tests_source, item.tests_source["4"]);

    await t.api("POST", `/api/sessions/${s.id}/end`, {});
    const review = await t.api("GET", `/api/sessions/${s.id}/review`);
    assert.equal(review.results.timed.levels_completed, 4);
    assert.deepEqual(review.results.levels.map((lv) => lv.completed_at), [700, 1300, 1900, 2500]);
    assert.deepEqual(review.results.levels.map((lv) => lv.split), [700, 600, 600, 600]);
    assert.equal(review.results.runs, 1);
    assert.equal(review.results.submits, 4);
    assert.equal(review.reference_code, item.reference_code);
    const list = await t.api("GET", "/api/problems");
    assert.equal(list.problems.find((p) => p.id === CODING).best_timed_levels, 4);
  });

  test("a failing hidden test leaves the level open, with the counts to show for it", async () => {
    const t = tab();
    const s = await t.api("POST", "/api/sessions", { problem_id: CODING, mode: "strict" });
    let first = true;
    t.python.verdict = (x) => {
      if (x.visibility === "hidden" && first) { first = false; return false; }
      return true;
    };
    const res = await t.api("POST", `/api/sessions/${s.id}/submit`, {});
    assert.equal(res.all_passed, false);
    assert.equal(res.unlocked, null);
    const counts = res.breakdown["1"];
    assert.equal(counts.hidden_passed, counts.hidden_total - 1);
    assert.equal(counts.shown_passed, counts.shown_total);
    await t.api("POST", `/api/sessions/${s.id}/end`, {});
    const review = await t.api("GET", `/api/sessions/${s.id}/review`);
    assert.equal(review.results.timed.levels_completed, 0);
    assert.deepEqual(review.results.timed.stopped_level_ratio, {
      passed: counts.shown_total + counts.hidden_total - 1,
      total: counts.shown_total + counts.hidden_total,
      shown_passed: counts.shown_total,
      shown_total: counts.shown_total,
      hidden_passed: counts.hidden_total - 1,
      hidden_total: counts.hidden_total,
    });
  });

  test("a level completed in overtime counts in the final result, not the timed one", async () => {
    const t = tab();
    const s = await t.api("POST", "/api/sessions", { problem_id: CODING, mode: "strict" });
    t.advance(LIMIT + 60);
    await t.api("POST", `/api/sessions/${s.id}/submit`, {});
    const timer = await t.api("GET", `/api/sessions/${s.id}/timer`);
    assert.equal(timer.overtime, true);
    assert.equal(timer.remaining, 0);
    await t.api("POST", `/api/sessions/${s.id}/end`, {});
    const { results } = await t.api("GET", `/api/sessions/${s.id}/review`);
    assert.equal(results.timed.levels_completed, 0);
    assert.equal(results.final.levels_completed, 1);
    assert.equal(results.levels[0].overtime, true);
    assert.equal(results.overtime_seconds, 60);
  });

  test("pausing stops the clock; strict sessions can't pause, and nothing saves while paused", async () => {
    const t = tab();
    const strict = await t.api("POST", "/api/sessions", { problem_id: CODING, mode: "strict" });
    await assert.rejects(t.api("POST", `/api/sessions/${strict.id}/pause`), { status: 409, message: /strict session/ });
    await t.api("POST", `/api/sessions/${strict.id}/end`);

    const s = await t.api("POST", "/api/sessions", { problem_id: CODING, mode: "pausable" });
    t.advance(10);
    assert.equal((await t.api("POST", `/api/sessions/${s.id}/pause`)).paused, true);
    t.advance(100);
    await assert.rejects(t.api("PUT", `/api/sessions/${s.id}/code`, { code: "x" }), { status: 409, message: /paused/ });
    await assert.rejects(t.api("POST", `/api/sessions/${s.id}/run`, {}), { message: /paused/ });
    assert.equal((await t.api("GET", `/api/sessions/${s.id}/timer`)).elapsed, 10);
    await t.api("POST", `/api/sessions/${s.id}/resume`);
    t.advance(5);
    assert.equal((await t.api("GET", `/api/sessions/${s.id}/timer`)).elapsed, 15);
    t.advance(LIMIT);
    await assert.rejects(t.api("POST", `/api/sessions/${s.id}/pause`), { message: /Time is up/ });
    await t.api("POST", `/api/sessions/${s.id}/end`);
    const review = await t.api("GET", `/api/sessions/${s.id}/review`);
    assert.equal(review.results.pauses.count, 1);
    assert.equal(review.results.pauses.total_seconds, 100);
  });

  test("one running session per track, and its problem's study pages wait until it ends", async () => {
    const t = tab();
    const s = await t.api("POST", "/api/sessions", { problem_id: CODING, mode: "strict" });
    await assert.rejects(t.api("POST", "/api/sessions", { problem_id: OTHER, mode: "strict" }), { status: 409 });
    await assert.rejects(t.api("GET", `/api/problems/${CODING}/reference`), { status: 409 });
    assert.ok((await t.api("GET", `/api/problems/${OTHER}/reference`)).reference_code);
    await assert.rejects(t.api("GET", `/api/sessions/${s.id}/review`), { status: 409 });
    // Another track can run alongside.
    await t.api("POST", "/api/algo/sessions", { problem_id: ALGO, mode: "strict" });
    assert.equal((await t.api("GET", "/api/active")).session.id, s.id);
    await t.api("POST", `/api/sessions/${s.id}/end`);
    assert.equal((await t.api("GET", "/api/active")).session, null);
    await assert.rejects(t.api("GET", `/api/sessions/${s.id}`), { status: 410 });
    assert.equal((await t.api("GET", `/api/problems/${CODING}/reference`)).reference_code, data.problems[0].reference_code);
  });

  test("a random start prefers a problem you haven't tried", async () => {
    const t = tab();
    const first = await t.api("POST", "/api/sessions", { mode: "strict" });
    assert.equal(first.problem.id, CODING); // random() is 0: the first of the pool
    await t.api("POST", `/api/sessions/${first.id}/end`);
    const second = await t.api("POST", "/api/sessions", { mode: "strict" });
    assert.equal(second.problem.id, OTHER);
  });

  test("scratch, lint and format", async () => {
    const t = tab();
    const s = await t.api("POST", "/api/sessions", { problem_id: CODING, mode: "strict" });
    const out = await t.api("POST", `/api/sessions/${s.id}/scratch`, { code: "c", scratch: "print(1)" });
    assert.equal(out.stdout, "scratch ran\n");
    assert.deepEqual(t.python.calls.at(-1), { code: "c", scratch: "print(1)" });
    assert.equal((await t.api("GET", `/api/sessions/${s.id}`)).scratch, "print(1)"); // saved

    const lint = await t.api("POST", `/api/sessions/${s.id}/lint`, { code: "import os\n" });
    assert.deepEqual(lint.issues.map((i) => i.code), ["F401"]);
    assert.deepEqual(t.ruff.calls.at(-1).settings, data.ruff.coding);
    assert.deepEqual(await t.api("POST", "/api/format", { code: "x=1  " }), { code: "x=1\n", error: null });

    t.ruff.broken = true;
    const broken = await t.api("POST", `/api/sessions/${s.id}/lint`, { code: "x" });
    assert.deepEqual(broken.issues, []);
    assert.match(broken.error, /Lint is unavailable: no wasm/);
    assert.deepEqual(await t.api("POST", "/api/format", { code: "x" }), { code: null, error: "no wasm" });
    const run = await t.api("POST", `/api/sessions/${s.id}/run`, {});
    assert.match(run.lint.error, /unavailable/); // a run still reports its tests
    assert.equal(run.all_passed, true);
  });
});

describe("storage", () => {
  test("a run records its result on top of what another tab saved meanwhile", async () => {
    const storage = memoryStorage();
    const clock = { now: 1_000_000 };
    const a = tab({ storage, clock });
    const b = tab({ storage, clock });
    const s = await a.api("POST", "/api/sessions", { problem_id: CODING, mode: "strict" });
    const release = a.python.hold();
    const running = a.api("POST", `/api/sessions/${s.id}/submit`, { code: "from tab a" });
    await new Promise((resolve) => setImmediate(resolve));
    await b.api("PUT", `/api/sessions/${s.id}/code`, { scratch: "tab b's scratch" });
    release();
    const res = await running;
    assert.equal(res.unlocked.completed, 1);
    const now = await b.api("GET", `/api/sessions/${s.id}`);
    assert.equal(now.scratch, "tab b's scratch");
    assert.equal(now.code, "from tab a");
    assert.equal(now.current_level, 2);
  });

  test("storage that refuses writes is reported once, and the page carries on", async () => {
    const storage = { get: () => null, set: () => { throw new Error("quota exceeded"); } };
    const t = tab({ storage });
    const s = await t.api("POST", "/api/sessions", { problem_id: CODING, mode: "strict" });
    await t.api("PUT", `/api/sessions/${s.id}/code`, { code: "kept in memory" });
    assert.equal((await t.api("GET", `/api/sessions/${s.id}`)).code, "kept in memory");
    assert.equal(t.storageErrors.length, 1);
    assert.match(t.storageErrors[0], /quota exceeded/);
  });

  test("answers are copies, and unknown routes are 404", async () => {
    const t = tab();
    const s = await t.api("POST", "/api/sessions", { problem_id: CODING, mode: "strict" });
    s.code = "changed by the page";
    assert.notEqual((await t.api("GET", `/api/sessions/${s.id}`)).code, "changed by the page");
    await assert.rejects(t.api("GET", "/api/nope"), { status: 404 });
    await assert.rejects(t.api("GET", "/api/sessions/99"), { status: 404 });
    await assert.rejects(t.api("POST", "/api/sessions", { problem_id: "nope", mode: "strict" }), { status: 404 });
    await assert.rejects(t.api("POST", "/api/sessions", { problem_id: CODING, mode: "slow" }), { status: 400 });
  });
});

describe("algorithm sessions", () => {
  test("Run checks the examples; the first submit that passes everything solves it", async () => {
    const t = tab();
    const file = await testsFile("algo", ALGO);
    const s = await t.api("POST", "/api/algo/sessions", { problem_id: ALGO, mode: "strict" });
    assert.equal((await t.api("GET", `/api/algo/sessions/${s.id}/timer`)).limit, data.algo.problems[0].problem.minutes * 60);

    const run = await t.api("POST", `/api/algo/sessions/${s.id}/run`, { code: "mine" });
    const job = t.python.calls[0];
    assert.deepEqual(job.tests.map((x) => x.id), file.tests.filter((x) => x.visibility === "shown").map((x) => x.id));
    assert.deepEqual(job.options, file.options);
    assert.equal(run.solved, false);
    assert.deepEqual(t.ruff.calls.at(-1).settings, data.ruff.algo);

    t.advance(60);
    const hidden = file.tests.filter((x) => x.visibility === "hidden");
    t.python.verdict = (x) => (x.id === hidden[0].id ? "Too slow: stopped after 750 ms; the limit for this test is 500 ms." : true);
    const slow = await t.api("POST", `/api/algo/sessions/${s.id}/submit`, {});
    assert.equal(slow.solved, false);
    assert.equal(slow.counts.too_slow, 1);
    assert.equal(slow.counts.hidden_passed, hidden.length - 1);

    t.advance(60);
    t.python.verdict = () => true;
    const solved = await t.api("POST", `/api/algo/sessions/${s.id}/submit`, {});
    assert.equal(solved.solved, true);
    assert.equal(solved.solved_at, 120);
    t.advance(60);
    const again = await t.api("POST", `/api/algo/sessions/${s.id}/submit`, {});
    assert.equal(again.solved, false);
    assert.equal(again.solved_at, 120);

    await t.api("POST", `/api/algo/sessions/${s.id}/end`, {});
    const review = await t.api("GET", `/api/algo/sessions/${s.id}/review`);
    assert.equal(review.results.timed.solved, true);
    assert.equal(review.results.final.best.passed, file.tests.length);
    assert.equal(review.results.final.best.elapsed, 120); // the earliest of the best
    assert.equal(review.results.runs, 1);
    assert.equal(review.results.submits, 3);
    const entry = (await t.api("GET", "/api/algo/problems")).problems.find((p) => p.id === ALGO);
    assert.deepEqual([entry.attempts, entry.solved, entry.solved_in_time, entry.best_time], [1, true, true, 120]);
  });

  test("scratch gets helpers.py beside the solution", async () => {
    const t = tab();
    const s = await t.api("POST", "/api/algo/sessions", { problem_id: ALGO, mode: "strict" });
    await t.api("POST", `/api/algo/sessions/${s.id}/scratch`, {});
    const job = t.python.calls[0];
    assert.equal(job.scratch, data.algo.problems[0].scratch_starter);
    assert.equal(job.files["helpers.py"], await readSiteText("py/helpers.py"));
  });

  test("a random start can be narrowed by difficulty and pattern", async () => {
    const t = tab();
    const hard = data.algo.problems.find((p) => p.problem.difficulty === "Hard").problem;
    const s = await t.api("POST", "/api/algo/sessions", { mode: "strict", difficulty: "Hard", pattern: hard.patterns[0] });
    assert.equal(s.problem.difficulty, "Hard");
    assert.ok(s.problem.patterns.includes(hard.patterns[0]));
    await t.api("POST", `/api/algo/sessions/${s.id}/end`);
    await assert.rejects(t.api("POST", "/api/algo/sessions", { mode: "strict", difficulty: "Easy", pattern: "nope" }), { status: 400 });
  });
});

describe("system design sessions", () => {
  test("steps go forward, the time on each is measured, and the self-check scores it", async () => {
    const t = tab();
    let s = await t.api("POST", "/api/design/sessions", { question_id: DESIGN, mode: "strict" });
    assert.deepEqual(s.step_starts, { 1: 0 });
    t.advance(300);
    s = await t.api("POST", `/api/design/sessions/${s.id}/step`, { step: 3 });
    assert.equal(s.current_step, 3);
    await assert.rejects(t.api("POST", `/api/design/sessions/${s.id}/step`, { step: 2 }), { status: 400 });
    await t.api("PUT", `/api/design/sessions/${s.id}/notes`, { notes: { 3: "a cache", 99: "ignored" }, diagram: { nodes: [] } });
    t.advance(120);
    await t.api("POST", `/api/design/sessions/${s.id}/end`, { notes: { 3: "a cache, sharded" } });
    await assert.rejects(t.api("PUT", `/api/design/sessions/${s.id}/notes`, { notes: {} }), { status: 409 });

    let review = await t.api("GET", `/api/design/sessions/${s.id}/review`);
    assert.equal(review.notes["3"], "a cache, sharded");
    assert.equal(review.notes["99"], undefined);
    assert.deepEqual(review.diagram, { nodes: [] });
    const spent = Object.fromEntries(review.results.steps.map((st) => [st.step, st.spent]));
    assert.deepEqual([spent[1], spent[2], spent[3]], [300, null, 120]);
    assert.equal(review.score, null);

    await assert.rejects(t.api("PUT", `/api/design/sessions/${s.id}/assessment`, { checklist: [999], key_points: [] }), { status: 400 });
    const got = await t.api("PUT", `/api/design/sessions/${s.id}/assessment`, { checklist: [2, 0, 2], key_points: [1] });
    assert.deepEqual(got.assessment, { checklist: [0, 2], key_points: [1] });
    review = await t.api("GET", `/api/design/sessions/${s.id}/review`);
    const total = data.design.checklist.length + data.design.questions[0].key_points.length;
    assert.deepEqual(review.score, { done: 3, total, checklist: 2, key_points: 1 });
    const listed = (await t.api("GET", "/api/design/questions")).questions.find((q) => q.id === DESIGN);
    assert.equal(listed.best.done, 3);
  });
});

describe("Java and C++ sessions", () => {
  test("a coding session in Java gets its files, and each run calls the current level's harness", async () => {
    const t = tab();
    const item = data.problems[0];
    const file = await testsFile("coding", CODING);
    let s = await t.api("POST", "/api/sessions", { problem_id: CODING, mode: "strict", language: "java" });
    assert.equal(s.language, "java");
    assert.deepEqual(s.files, { solution: item.langs.java.file, scratch: "Scratch.java", tests: "Tests.java" });
    assert.equal(s.code, item.langs.java.starter_code);
    assert.equal(s.scratch, item.langs.java.scratch_starter);
    assert.equal(s.tests_source, item.langs.java.tests_source["1"]);
    assert.equal(s.levels[0].stubs, item.langs.java.stubs["1"]);

    const run = await t.api("POST", `/api/sessions/${s.id}/run`, { code: "class X {}" });
    const job = t.java.calls.at(-1);
    assert.equal(job.code, "class X {}");
    assert.equal(job.lang.harness, file.langs.java.harness["1"]);
    assert.deepEqual(job.lang.files, file.langs.java.files);
    assert.equal(t.python.calls.length, 0);
    assert.equal(t.ruff.calls.length, 0); // the compiler's warnings are the lint
    assert.deepEqual(run.lint.issues.map((i) => i.code), ["warning"]);
    assert.equal(run.compile_error, false);

    s = (await t.api("POST", `/api/sessions/${s.id}/submit`, {})).session;
    assert.equal(s.current_level, 2);
    assert.equal(s.levels[1].stubs, item.langs.java.stubs["2"]);
    assert.equal(s.tests_source, item.langs.java.tests_source["2"]);
    await t.api("POST", `/api/sessions/${s.id}/run`, {});
    assert.equal(t.java.calls.at(-1).lang.harness, file.langs.java.harness["2"]);

    const scratch = await t.api("POST", `/api/sessions/${s.id}/scratch`, { scratch: "class Scratch {}" });
    assert.equal(scratch.stdout, "compiled scratch\n");
    assert.equal(t.java.calls.at(-1).scratch, "class Scratch {}");
    await t.api("POST", `/api/sessions/${s.id}/lint`, { code: "y" });
    assert.equal(t.java.calls.at(-1).code, "y");

    await t.api("POST", `/api/sessions/${s.id}/end`, {});
    const review = await t.api("GET", `/api/sessions/${s.id}/review`);
    assert.equal(review.language, "java");
    assert.equal(review.reference_code, item.reference_code); // the reference stays Python
    assert.equal((await t.api("GET", "/api/history")).sessions[0].language, "java");
  });

  test("an algorithms session in C++ runs the problem's harness", async () => {
    const t = tab();
    const item = data.algo.problems[0];
    const file = await testsFile("algo", ALGO);
    const s = await t.api("POST", "/api/algo/sessions", { problem_id: ALGO, mode: "strict", language: "cpp" });
    assert.equal(s.code, item.langs.cpp.starter_code);
    assert.equal(s.signature, item.langs.cpp.signature);
    assert.deepEqual(s.files, { solution: "solution.cpp", scratch: "scratch.cpp", tests: "tests.cpp" });
    await t.api("POST", `/api/algo/sessions/${s.id}/submit`, { code: "int x;" });
    const job = t.cpp.calls.at(-1);
    assert.equal(job.lang.harness, file.langs.cpp.harness);
    assert.deepEqual(job.options, file.options);
    assert.equal(job.tests.length, file.tests.length);
    await t.api("POST", `/api/algo/sessions/${s.id}/scratch`, {});
    assert.deepEqual(t.cpp.calls.at(-1).lang, file.langs.cpp);
    assert.equal((await t.api("GET", "/api/algo/history")).sessions[0].language, "cpp");
  });

  test("sessions are Python unless they say otherwise, and other languages are refused", async () => {
    const t = tab();
    await assert.rejects(t.api("POST", "/api/sessions", { problem_id: CODING, mode: "strict", language: "cobol" }), { status: 400 });
    await assert.rejects(t.api("POST", "/api/algo/sessions", { problem_id: ALGO, mode: "strict", language: "c#" }), { status: 400 });
    const s = await t.api("POST", "/api/sessions", { problem_id: CODING, mode: "strict" });
    assert.equal(s.language, "python");
    assert.equal(s.files.solution, "solution.py");
  });
});

describe("history export and import", () => {
  async function someHistory(t) {
    const c = await t.api("POST", "/api/sessions", { problem_id: CODING, mode: "strict" });
    await t.api("POST", `/api/sessions/${c.id}/submit`, {});
    await t.api("POST", `/api/sessions/${c.id}/end`);
    t.advance(10);
    const a = await t.api("POST", "/api/algo/sessions", { problem_id: ALGO, mode: "pausable" });
    await t.api("POST", `/api/algo/sessions/${a.id}/submit`, {});
    await t.api("POST", `/api/algo/sessions/${a.id}/end`);
    t.advance(10);
    const d = await t.api("POST", "/api/design/sessions", { question_id: DESIGN, mode: "strict" });
    await t.api("POST", `/api/design/sessions/${d.id}/end`);
    t.advance(10);
    await t.api("POST", "/api/sessions", { problem_id: OTHER, mode: "strict" }); // still running
  }

  test("an export loads into another browser, once", async () => {
    const a = tab();
    await someHistory(a);
    const exported = await a.api("GET", "/api/backup");
    assert.equal(exported.format, "swe-prac-history");
    assert.equal(exported.version, 1);

    const b = tab();
    const added = await b.api("POST", "/api/backup", JSON.parse(JSON.stringify(exported)));
    assert.deepEqual(added, { ok: true, added: { coding: 2, algo: 1, design: 1 } });
    for (const path of ["/api/history", "/api/algo/history", "/api/design/history"]) {
      assert.deepEqual(await b.api("GET", path), await a.api("GET", path), path);
    }
    assert.equal((await b.api("GET", "/api/active")).session.problem.id, OTHER);
    const again = await b.api("POST", "/api/backup", exported);
    assert.deepEqual(again.added, { coding: 0, algo: 0, design: 0 });
  });

  test("a running session from the file ends if this browser already has one running", async () => {
    const a = tab();
    await someHistory(a);
    const exported = await a.api("GET", "/api/backup");
    const b = tab({ clock: { now: 2_000_000 } });
    const mine = await b.api("POST", "/api/sessions", { problem_id: CODING, mode: "strict" });
    await b.api("POST", "/api/backup", exported);
    const history = (await b.api("GET", "/api/history")).sessions;
    assert.equal(history.filter((s) => s.status === "active").length, 1);
    assert.equal((await b.api("GET", "/api/active")).session.id, mine.id);
    assert.equal(history.find((s) => s.problem_id === OTHER).status, "finished");
    assert.equal(new Set(history.map((s) => s.id)).size, history.length); // fresh ids
  });

  test("files that aren't an export are refused", async () => {
    const t = tab();
    await assert.rejects(t.api("POST", "/api/backup", { hello: 1 }), { status: 400, message: /isn't a history export/ });
    await assert.rejects(t.api("POST", "/api/backup", { format: "swe-prac-history", version: 2 }), { status: 400, message: /newer version/ });
    await assert.rejects(
      t.api("POST", "/api/backup", { format: "swe-prac-history", version: 1, coding: { sessions: [{ problem_id: CODING }] } }),
      { status: 400, message: /started_at/ },
    );
    assert.deepEqual((await t.api("GET", "/api/history")).sessions, []);
  });
});
