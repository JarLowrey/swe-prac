// Judging a Java or C++ run: the compiled harness (static/lang/) calls the solution and reports
// what each call returned; this compares that with the expected answers and reports each test
// the way runner.py does for Python ({event: "start" | "call" | "end" | "stopped" | "done"}), so
// the rest of the app treats every language alike.
//
// lang-run.js uses it in the run worker, and tests/js/ uses it directly.

export const MAX_REPR_CHARS = 2000;
export const MAX_STDOUT_CHARS = 20000;

/** Test data with {"__tuple__": [...]} markers as plain lists (the harnesses take lists). */
export function plain(value) {
  if (Array.isArray(value)) return value.map(plain);
  if (value && typeof value === "object") {
    const keys = Object.keys(value);
    if (keys.length === 1 && keys[0] === "__tuple__") return value.__tuple__.map(plain);
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, plain(v)]));
  }
  return value;
}

/** A value as Java and C++ code would write it in a test: [1, 2], "text", null, true. */
export function show(value) {
  if (value === null || value === undefined) return "null";
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(show).join(", ")}]`;
  if (typeof value === "object") {
    const keys = Object.keys(value);
    if (keys.length === 1 && keys[0] === "__tuple__") return show(value.__tuple__);
    return `{${Object.entries(value).map(([k, v]) => `${JSON.stringify(k)}: ${show(v)}`).join(", ")}}`;
  }
  return String(value);
}

export function shortShow(value) {
  const text = show(value);
  return text.length > MAX_REPR_CHARS ? `${text.slice(0, MAX_REPR_CHARS)}...<truncated>` : text;
}

/** runner.matches: bools must be bools, null must be null, numbers compare by value. */
export function matches(expected, actual) {
  if (expected === null || expected === undefined) return actual === null;
  if (typeof expected === "boolean") return actual === expected;
  if (typeof expected === "number") return typeof actual === "number" && actual === expected;
  if (typeof expected === "string") return actual === expected;
  if (Array.isArray(expected)) {
    return Array.isArray(actual) && actual.length === expected.length && expected.every((e, i) => matches(e, actual[i]));
  }
  if (typeof expected === "object") {
    if (!actual || typeof actual !== "object" || Array.isArray(actual)) return false;
    const keys = Object.keys(expected);
    return keys.length === Object.keys(actual).length && keys.every((k) => k in actual && matches(expected[k], actual[k]));
  }
  return false;
}

// A key that sorts equal values together, as runner._sort_key (json.dumps, sorted keys) does.
function sortKey(value) {
  if (Array.isArray(value)) return `[${value.map(sortKey).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${sortKey(value[k])}`).join(",")}}`;
  }
  return JSON.stringify(value ?? null);
}

const sorted = (list) => [...list].sort((a, b) => {
  const x = sortKey(a);
  const y = sortKey(b);
  return x < y ? -1 : x > y ? 1 : 0;
});

/** runner.compare: [passed, message], message explaining a failure the values don't show. */
export function compare(options, args, expect, actual, checker) {
  const mode = options?.compare ?? "exact";
  if (mode === "exact") return [matches(expect, actual), null];
  if (mode === "unordered" || mode === "unordered_nested") {
    if (!Array.isArray(actual)) return [false, null];
    let a = actual;
    let e = expect;
    if (mode === "unordered_nested") {
      if (!a.every(Array.isArray)) return [false, null];
      a = a.map(sorted);
      e = e.map(sorted);
    }
    return [matches(sorted(e), sorted(a)), null];
  }
  if (mode === "validator") {
    const verdict = checker(args, expect, actual);
    if (typeof verdict === "string") return [false, verdict];
    return [Boolean(verdict), null];
  }
  throw new Error(`unknown compare mode ${mode}`);
}

/** The problem's checker (options.validator_js: the source of check(args, expect, actual)). */
export function checkerFor(options) {
  if (options?.compare !== "validator") return null;
  // eslint-disable-next-line no-new-func -- the problem's own checker, from the site's files
  return new Function(`${options.validator_js}\nreturn check;`)();
}

const fmt = (n) => n.toLocaleString("en-US", { maximumFractionDigits: 0 });

/**
 * Follows one run: feed it the harness's events (onEvent) and the program's output (onOutput);
 * it posts runner-style events through `post`. `names` maps the tests' method names to the
 * language's (add_file -> addFile), for showing calls.
 */
export class Judge {
  constructor({ tests, options = {}, names = {}, post, now = () => performance.now() }) {
    this.tests = tests;
    this.options = options;
    this.names = names;
    this.post = post;
    this.now = now;
    this.checker = checkerFor(options);
    this.next = 0; // index of the next test to start
    this.current = null; // {test, steps, stepIndex, stdout, started, passed, error, failedStep}
  }

  /** The harness's input for the tests from `from` on: their calls and arguments only. */
  input(from = 0) {
    const tests = this.tests.slice(from).map((t) => ({
      steps: t.steps.map((s) => ({ call: s.call, args: plain(s.args) })),
    }));
    return `${JSON.stringify({ tests })}\n`;
  }

  get remaining() {
    return this.tests.length - this.next;
  }

  onOutput(text) {
    const c = this.current;
    if (!c || !text) return;
    const left = MAX_STDOUT_CHARS - c.stdout.length;
    if (left <= 0) return;
    c.stdout += text.length > left ? `${text.slice(0, left)}\n...<output truncated>\n` : text;
  }

  /** One harness event. Returns false after a step that ends its test (a failed one). */
  onEvent(event) {
    if (event.e === "start") {
      const test = this.tests[this.next++];
      this.current = { test, steps: [], stepIndex: 0, stdout: "", started: this.now(), passed: true, error: null, failedStep: null };
      this.post({ event: "start", id: test.id });
      return true;
    }
    const c = this.current;
    if (event.e === "call") {
      if (c?.test.limit_ms) this.post({ event: "call", id: c.test.id, limit_ms: c.test.limit_ms });
      return true;
    }
    if (event.e === "ctor") {
      c.passed = false;
      c.error = `Error constructing the class:\n${event.raised}`;
      return true;
    }
    if (event.e === "step") return this.step(event);
    if (event.e === "end") {
      this.end();
      return true;
    }
    if (event.e === "done") {
      this.post({ event: "done" });
      return true;
    }
    return true;
  }

  record(step) {
    const record = {
      call: this.names[step.call] ?? step.call,
      args: step.args.map(shortShow).join(", "),
      checked: "expect" in step,
    };
    if ("expect" in step) record.expect = shortShow(step.expect);
    return record;
  }

  step(event) {
    const c = this.current;
    const index = c.stepIndex++;
    const step = c.test.steps[index];
    const record = this.record(step);
    const fail = (actual, error) => {
      record.ok = false;
      record.actual = actual;
      c.steps.push(record);
      c.passed = false;
      c.failedStep = index;
      c.error = error;
      return false;
    };
    if (event.raised != null) {
      const type = String(event.raised).split(/[:\n]/)[0].split(".").pop();
      return fail(`<raised ${type}>`, event.raised);
    }
    if (event.adapter != null) return fail(`<${event.adapter}>`, event.adapter);
    const actual = event.value;
    record.actual = shortShow(actual);
    let ok = true;
    let message = null;
    if ("expect" in step) {
      [ok, message] = compare(this.options, plain(step.args), plain(step.expect), actual, this.checker);
    }
    const limit = c.test.limit_ms;
    if (ok && limit && event.ms > limit) {
      ok = false;
      message = `Too slow: this test took ${fmt(event.ms)} ms and the limit is ${fmt(limit)} ms. The answer was right; look for a faster algorithm.`;
    }
    record.ok = ok;
    c.steps.push(record);
    if (!ok) {
      c.passed = false;
      c.failedStep = index;
      c.error = message;
    }
    return ok;
  }

  end() {
    const c = this.current;
    if (!c) return;
    this.current = null;
    this.post({
      event: "end",
      id: c.test.id,
      passed: c.passed,
      steps: c.steps,
      total_steps: c.test.steps.length,
      failed_step: c.failedStep,
      error: c.error,
      stdout: c.stdout,
      ms: Math.round((this.now() - c.started) * 100) / 100,
    });
  }

  /**
   * The program stopped during a test (a trap, such as Java's NullPointerException, or exit()):
   * that test fails with `error`. Returns true if tests remain to run in a fresh instance.
   */
  crash(error, actual = "<crashed>") {
    const c = this.current;
    if (c) {
      const index = c.stepIndex;
      const step = c.test.steps[index];
      if (step) {
        const record = this.record(step);
        record.ok = false;
        record.actual = actual;
        c.steps.push(record);
        c.failedStep = index;
      }
      c.passed = false;
      c.error = c.error ?? error;
      this.end();
    }
    return this.remaining > 0;
  }
}
