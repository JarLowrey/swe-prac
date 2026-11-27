// Running Java and C++ on the page: compile (lang-compile.js, a worker that stays loaded), then
// run the program in a fresh worker (lang-run.js) that the page ends if it runs too long, as
// python.js does for Python. Each language gets the same interface as python.js:
//
//   runTests({code, tests, options, lang})   -> the run, as python.js reports it, plus
//                                               compile_error and lint (the build's warnings)
//   runScratch({code, scratch, lang})        -> {stdout, stderr, exit_code, timed_out, crashed, ms}
//   lint({code, lang})                       -> {issues, error}, the compiler's diagnostics
//   warmUp(), coolDown()
//
// `lang` is the problem's part of its tests file for this language (tools/build_static.py):
// {file, files, harness, names}. A compile is reused while the sources are the same.

const RUN_TIMEOUT_SECONDS = 10; // the whole run, as for Python
const SCRATCH_TIMEOUT_SECONDS = 10;
const LIMIT_GRACE = 1.5; // a call is stopped at 1.5 times its limit, as for Python
// Messages between the run worker and the page take a moment, and the limits are short: the
// page stops a call only well past its limit (the worker's own timing decides "too slow").
const WATCHDOG_SLACK_MS = 1000;
const BOOT_TIMEOUT_SECONDS = 600; // the first C++ load downloads about 40 MB
const JAVA_BUILDS_PER_WORKER = 6; // the Java compiler grows with each build: start afresh

// The time limits are set for Python (500 ms on most large tests, where the reference takes under
// 10 ms and the naive approach over 500). Java and C++ get a tenth of them: measured on the large
// tests, efficient solutions take under 10 ms in both, naive ones 50 to 250 ms.
export const TIME_FACTOR = { java: 0.1, cpp: 0.1 };

/** The tests with their time limits scaled to `lang`'s. */
export function scaleLimits(tests, lang) {
  return tests.map((t) => (t.limit_ms ? { ...t, limit_ms: Math.max(1, Math.round(t.limit_ms * TIME_FACTOR[lang])) } : t));
}

export const LABEL = { java: "Java", cpp: "C++" };
const DOWNLOAD = { java: "about 8 MB", cpp: "about 40 MB" };
const SCRATCH_FILE = { java: "Scratch.java", cpp: "scratch.cpp" };

function status(state, text) {
  window.dispatchEvent(new CustomEvent("swe-runner", { detail: { state, text } }));
}

const fmt = (n) => n.toLocaleString("en-US", { maximumFractionDigits: 0 });

function workerUrl(name, lang) {
  const url = new URL(name, import.meta.url);
  url.searchParams.set("lang", lang);
  return url;
}

// A worker that posts {type: "ready"} or {type: "boot-error"} first.
function spawn(name, lang, onProgress) {
  const worker = new Worker(workerUrl(name, lang), { type: "module" });
  let timer = null;
  const ready = new Promise((resolve, reject) => {
    timer = setTimeout(() => reject(new Error(`${LABEL[lang]} took too long to load.`)), BOOT_TIMEOUT_SECONDS * 1000);
    worker.onmessage = ({ data }) => {
      if (data.type === "ready") { clearTimeout(timer); resolve(); }
      if (data.type === "boot-error") { clearTimeout(timer); reject(new Error(data.message)); }
      if (data.type === "progress") onProgress?.(data.text);
    };
    worker.onerror = (e) => {
      clearTimeout(timer);
      reject(new Error(e.message || `The ${LABEL[lang]} worker failed to start.`));
    };
  });
  ready.catch(() => worker.terminate());
  return { worker, ready, stop: () => { clearTimeout(timer); worker.terminate(); } };
}

/** Compiler diagnostics as the Lint tab lists them (ruff's shape: 1-based rows and columns). */
export function lintIssues(diagnostics, file) {
  return diagnostics
    .filter((d) => d.file === file && d.line)
    .map((d) => ({
      code: d.severity,
      message: d.message.split("\n")[0],
      row: d.line,
      col: d.col ?? 1,
      end_row: d.line,
      end_col: (d.col ?? 1) + 1,
      fixable: false,
    }))
    .sort((a, b) => a.row - b.row || a.col - b.col);
}

/** Compile errors as text, the solution's first. `harness` is the file the tests' code is in. */
export function compileErrorText(diagnostics, { file, harness }) {
  const errors = diagnostics.filter((d) => d.severity === "error");
  const where = (d) => [d.file, d.line, d.col].filter(Boolean).join(":");
  const text = (list) => list.map((d) => `${where(d)}${where(d) ? ": " : ""}error: ${d.message}`).join("\n");
  const mine = errors.filter((d) => d.file !== harness);
  const theirs = errors.filter((d) => d.file === harness);
  const parts = [];
  if (mine.length) parts.push(text(mine));
  if (theirs.length) {
    parts.push(`The tests call your methods as the starter code declares them (names, parameter and return types). Keep those signatures.\n${text(theirs)}`);
  }
  return parts.join("\n\n") || "The code didn't compile.";
}

function language(lang) {
  let compiler = null; // {worker, ready, stop, pending: Map, builds}
  let spare = null; // a run worker started ahead of the next job
  let nextId = 1;
  const cache = new Map(); // sources key -> compile result (the last few)

  function startCompiler() {
    const onProgress = (text) => status("loading", `Downloading the ${LABEL[lang]} compiler… ${text}`);
    const c = { ...spawn("lang-compile.js", lang, onProgress), pending: new Map(), builds: 0 };
    c.ready.then(() => {
      c.worker.onmessage = ({ data }) => {
        const job = c.pending.get(data.id);
        if (!job) return;
        c.pending.delete(data.id);
        if (data.type === "result") job.resolve(data.result);
        else job.reject(new Error(data.message));
      };
      c.worker.onerror = (e) => {
        e.preventDefault?.();
        for (const job of c.pending.values()) job.reject(new Error(e.message || "The compiler stopped."));
        c.pending.clear();
        if (compiler === c) compiler = null;
        c.stop();
      };
    }, () => { if (compiler === c) compiler = null; });
    return c;
  }

  function warmCompiler() {
    compiler ??= startCompiler();
    return compiler.ready;
  }

  function warmRunner() {
    if (!spare) {
      const w = spawn("lang-run.js", lang);
      spare = w;
      w.ready.catch(() => { if (spare === w) spare = null; });
    }
    return spare.ready;
  }

  async function compileOnce(request) {
    if (compiler && lang === "java" && compiler.builds >= JAVA_BUILDS_PER_WORKER && !compiler.pending.size) {
      compiler.stop();
      compiler = null;
    }
    const slow = setTimeout(() => status("loading", `Starting ${LABEL[lang]}… (the first run downloads ${DOWNLOAD[lang]})`), 300);
    try {
      await warmCompiler();
    } catch (err) {
      throw new Error(`Couldn't start ${LABEL[lang]} in this browser: ${err.message}`);
    } finally {
      clearTimeout(slow);
    }
    const c = compiler;
    if (request.mode === "build") c.builds += 1;
    const id = nextId++;
    return new Promise((resolve, reject) => {
      c.pending.set(id, { resolve, reject });
      c.worker.postMessage({ id, ...request });
    });
  }

  // Compile, reusing an earlier result for the same sources. A Java compiler that fails
  // internally (it can, after many builds) is replaced and tried once more.
  async function compile(request) {
    const key = JSON.stringify([request.main, request.mode, Object.entries(request.files).sort()]);
    if (cache.has(key)) return cache.get(key);
    if (request.mode === "build") status("compiling", "Compiling…");
    let result;
    try {
      result = await compileOnce(request);
    } catch (err) {
      if (lang !== "java" || !compiler) throw err;
      compiler.stop();
      compiler = null;
      result = await compileOnce(request);
    }
    cache.set(key, result);
    if (cache.size > 6) cache.delete(cache.keys().next().value);
    return result;
  }

  async function take() {
    warmRunner();
    const w = spare;
    spare = null;
    try {
      await w.ready;
    } catch (err) {
      throw new Error(`Couldn't start ${LABEL[lang]} in this browser: ${err.message}`);
    }
    status("running", "Running…");
    return w;
  }

  function warmUp() {
    return Promise.all([warmCompiler(), warmRunner()]);
  }

  function coolDown() {
    spare?.stop();
    spare = null;
    compiler?.stop();
    compiler = null;
  }

  const scaled = (tests) => scaleLimits(tests, lang);

  async function runTests({ code, tests, options, lang: files }) {
    const harnessFile = lang === "java" ? "SweMain.java" : "main.cpp";
    const sources = { ...files.files, [files.file]: code, [harnessFile]: files.harness };
    const build = await compile({ files: sources, main: lang === "java" ? "SweMain" : "main.cpp", mode: "build" });
    const run = {
      import_error: null, import_stdout: "", timed_out: false, crashed: null, stopped: null, results: {}, ms: 0,
      compile_error: false,
      lint: { issues: lintIssues(build.diagnostics, files.file), error: null }, // the build's warnings
    };
    if (!build.ok) {
      run.import_error = compileErrorText(build.diagnostics, { file: files.file, harness: harnessFile });
      run.compile_error = true;
      return run;
    }
    const w = await take();
    const job = { kind: "tests", lang, wasm: build.wasm, tests: scaled(tests), options, names: files.names };
    return new Promise((resolve) => {
      let started = null;
      let current = null;
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
              : "The program stopped unexpectedly during this test.",
          };
        }
        run.ms = started === null ? 0 : Math.round((performance.now() - started) * 10) / 10;
        resolve(run);
        warmRunner();
      };

      const tooSlow = (id, limit, after) => {
        const error = `Too slow: stopped after ${fmt(after)} ms; the limit for this test is ${fmt(limit)} ms. Look for a faster algorithm.`;
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
          if (e.event === "start") {
            current = e.id;
          } else if (e.event === "call") {
            const after = Math.max(e.limit_ms * LIMIT_GRACE, e.limit_ms + WATCHDOG_SLACK_MS);
            watchdog = setTimeout(() => tooSlow(e.id, e.limit_ms, after), after);
          } else if (e.event === "end") {
            run.results[e.id] = e;
            current = null;
          } else if (e.event === "stopped") {
            run.stopped = e.reason;
          }
        } else if (data.type === "finished") {
          finish();
        } else if (data.type === "fatal") {
          run.crashed = `The ${LABEL[lang]} program stopped with an internal error:\n${data.message}`;
          finish();
        }
      };
      w.worker.onerror = (e) => {
        e.preventDefault();
        run.crashed = e.message || "The worker stopped.";
        finish();
      };
      w.worker.postMessage(job); // a copy: the compile stays cached for the next run
    });
  }

  async function runScratch({ code, scratch, lang: files }) {
    const scratchFile = SCRATCH_FILE[lang];
    const sources = { ...files.files, [files.file]: code, [scratchFile]: scratch };
    const build = await compile({ files: sources, main: lang === "java" ? "Scratch" : "scratch.cpp", mode: "build" });
    const out = { stdout: "", stderr: "", exit_code: null, timed_out: false, crashed: false, ms: 0 };
    if (!build.ok) {
      out.stderr = compileErrorText(build.diagnostics, { file: files.file, harness: null });
      out.exit_code = 1;
      return out;
    }
    const w = await take();
    return new Promise((resolve) => {
      let started = null;
      let whole = null;
      const finish = () => {
        clearTimeout(whole);
        w.stop();
        out.ms = started === null ? 0 : Math.round((performance.now() - started) * 10) / 10;
        resolve(out);
        warmRunner();
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
          out.stderr += `${out.stderr ? "\n" : ""}${data.message}`;
          finish();
        }
      };
      w.worker.onerror = (e) => {
        e.preventDefault();
        out.crashed = true;
        out.stderr += e.message || "The worker stopped.";
        finish();
      };
      w.worker.postMessage({ kind: "scratch", lang, wasm: build.wasm });
    });
  }

  // The compiler's errors and warnings for the solution alone (no tests), for the Lint tab.
  async function lint({ code, lang: files }) {
    const main = lang === "java" ? "SweMain" : files.file;
    const result = await compile({ files: { ...files.files, [files.file]: code }, main, mode: "check" });
    return { issues: lintIssues(result.diagnostics, files.file), error: null };
  }

  return { warmUp, coolDown, runTests, runScratch, lint };
}

export const java = language("java");
export const cpp = language("cpp");
