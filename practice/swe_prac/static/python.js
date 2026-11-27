// Running Python on the page: tests (Run and Submit) and scratch.py, each in a fresh Web Worker.
//
// Every job gets its own interpreter (py-worker.js), like a subprocess per run: nothing one run
// does can leak into the next, and a run that hangs or crashes is ended by terminating its
// worker. Loading Pyodide takes a second or two (and downloads about 13 MB the first time), so
// one worker is always started ahead: warmUp() when a session opens, and again after each job.
//
// runTests() resolves to what the runner reported, in the shape swe_prac/execution.py's TestRun
// had: {import_error, import_stdout, timed_out, crashed, stopped, results: {id: end event}, ms}.

const RUN_TIMEOUT_SECONDS = 10; // the whole run, as config.RUN_TIMEOUT_SECONDS
const SCRATCH_TIMEOUT_SECONDS = 10;
const LIMIT_GRACE = 1.5; // runner.LIMIT_GRACE: a call is stopped at 1.5 times its limit_ms
const BOOT_TIMEOUT_SECONDS = 180; // the first load downloads Pyodide

const STACK_NOTE = `Python ran out of stack and stopped. In the browser, recursion that passes
through built-in code is limited to a few hundred levels. Plain recursive calls are fine, and so
are functools.cache and max, min, sum, any, all and sorted over a generator. Recursion through
others, such as list(...), str.join(...) or map(...) over a generator, or a recursive __init__,
__eq__ or property, is not: rewrite that part as a plain recursive call or a loop. Dropping a
linked list or tree of many thousands of nodes that your code built can do this too.`.replace(/\n/g, " ");

let spare = null; // { worker, ready: Promise, stop() } started ahead of the next job

function spawn() {
  const worker = new Worker(new URL("py-worker.js", import.meta.url), { type: "module" });
  let timer = null;
  const ready = new Promise((resolve, reject) => {
    timer = setTimeout(() => reject(new Error("Python took too long to load.")), BOOT_TIMEOUT_SECONDS * 1000);
    worker.onmessage = ({ data }) => {
      if (data.type === "ready") { clearTimeout(timer); resolve(); }
      if (data.type === "boot-error") { clearTimeout(timer); reject(new Error(data.message)); }
    };
    worker.onerror = (e) => {
      clearTimeout(timer);
      reject(new Error(e.message || "The Python worker failed to start."));
    };
  });
  ready.catch(() => worker.terminate());
  const stop = () => {
    clearTimeout(timer);
    worker.terminate();
  };
  return { worker, ready, stop };
}

// Start loading Python now, so the next run doesn't wait for it.
export function warmUp() {
  if (!spare) {
    const w = spawn();
    spare = w;
    w.ready.catch(() => { if (spare === w) spare = null; }); // retried on the next job
  }
  return spare.ready;
}

// Free the spare interpreter (leaving a session page).
export function coolDown() {
  spare?.stop();
  spare = null;
}

// What a run is waiting on, for the session page: {state: "loading" | "running", text}
// (compiled.js reports Java and C++ the same way).
const STARTING = "Starting Python… (the first run downloads about 13 MB)";
function status(state) {
  const text = state === "loading" ? STARTING : "Running…";
  window.dispatchEvent(new CustomEvent("swe-runner", { detail: { state, text } }));
}

// A started worker for one job. Tells the page when it has to wait for Python to load.
async function take() {
  const w = spare ?? spawn();
  spare = null;
  const slow = setTimeout(() => status("loading"), 300);
  try {
    await w.ready;
  } catch (err) {
    throw new Error(`Couldn't start Python in this browser: ${err.message}`);
  } finally {
    clearTimeout(slow);
    status("running");
  }
  return w;
}

const crashText = (message) => (/call stack|stack size|too much recursion/i.test(message)
  ? `${STACK_NOTE}\n\n${message}` : `Python stopped with an internal error:\n${message}`);

const ms = (n) => n.toLocaleString("en-US", { maximumFractionDigits: 0 });

// Run `tests` against `code`; see runner.py for `options`.
export async function runTests({ code, className, tests, options }) {
  const w = await take();
  const run = { import_error: null, import_stdout: "", timed_out: false, crashed: null, stopped: null, results: {}, ms: 0 };
  return new Promise((resolve) => {
    let started = null;
    let current = null; // the test that started and hasn't ended
    let watchdog = null;
    let whole = null;

    const finish = () => {
      clearTimeout(watchdog);
      clearTimeout(whole);
      w.stop();
      if (current !== null && !run.results[current]) {
        run.results[current] = {
          id: current, passed: false, steps: [], failed_step: null, stdout: "", ms: null,
          timed_out: run.timed_out,
          error: run.timed_out
            ? `Timed out: the whole run exceeded ${RUN_TIMEOUT_SECONDS}s (infinite loop or very slow code?)`
            : "The test process exited unexpectedly during this test.",
        };
      }
      run.ms = started === null ? 0 : Math.round((performance.now() - started) * 10) / 10;
      resolve(run);
      warmUp();
    };

    // A call still running at 1.5 times its limit: report it as the runner does, and stop.
    const tooSlow = (id, limit) => {
      const error = `Too slow: stopped after ${ms(limit * LIMIT_GRACE)} ms; the limit for this test is ${ms(limit)} ms. Look for a faster algorithm.`;
      run.results[id] = { id, passed: false, steps: [], failed_step: 0, error, stdout: "", ms: null };
      run.stopped = error;
      current = null;
      finish();
    };

    w.worker.onmessage = ({ data }) => {
      if (data.type === "begin") {
        started = performance.now();
        whole = setTimeout(() => { run.timed_out = true; finish(); }, RUN_TIMEOUT_SECONDS * 1000);
      } else if (data.type === "event") {
        const e = data.event;
        clearTimeout(watchdog);
        if (e.event === "import_error") {
          run.import_error = e.error;
          run.import_stdout = e.stdout ?? "";
        } else if (e.event === "start") {
          current = e.id;
        } else if (e.event === "call") {
          watchdog = setTimeout(() => tooSlow(e.id, e.limit_ms), e.limit_ms * LIMIT_GRACE);
        } else if (e.event === "end") {
          run.results[e.id] = e;
          current = null;
        } else if (e.event === "stopped") {
          run.stopped = e.reason;
        }
      } else if (data.type === "finished") {
        finish();
      } else if (data.type === "fatal") {
        run.crashed = crashText(data.message);
        finish();
      }
    };
    w.worker.onerror = (e) => {
      e.preventDefault();
      run.crashed = crashText(e.message || "The worker stopped.");
      finish();
    };
    w.worker.postMessage({ kind: "tests", code, className, tests, options });
  });
}

// Run scratch.py with solution.py (and `files`, e.g. helpers.py) beside it.
export async function runScratch({ code, scratch, files }) {
  const w = await take();
  const out = { stdout: "", stderr: "", exit_code: null, timed_out: false, crashed: false, ms: 0 };
  return new Promise((resolve) => {
    let started = null;
    let whole = null;
    const finish = () => {
      clearTimeout(whole);
      w.stop();
      out.ms = started === null ? 0 : Math.round((performance.now() - started) * 10) / 10;
      resolve(out);
      warmUp();
    };
    w.worker.onmessage = ({ data }) => {
      if (data.type === "begin") {
        started = performance.now();
        whole = setTimeout(() => {
          out.timed_out = true;
          out.stderr += `\nTimed out after ${SCRATCH_TIMEOUT_SECONDS}s.`;
          finish();
        }, SCRATCH_TIMEOUT_SECONDS * 1000);
      } else if (data.type === "stdout") {
        out.stdout += data.text;
      } else if (data.type === "stderr") {
        out.stderr += data.text;
      } else if (data.type === "finished") {
        out.exit_code = data.exit_code;
        finish();
      } else if (data.type === "fatal") {
        out.crashed = true;
        out.stderr += `${out.stderr ? "\n" : ""}${crashText(data.message)}`;
        finish();
      }
    };
    w.worker.onerror = (e) => {
      e.preventDefault();
      out.crashed = true;
      out.stderr += crashText(e.message || "The worker stopped.");
      finish();
    };
    w.worker.postMessage({ kind: "scratch", code, scratch, files });
  });
}
