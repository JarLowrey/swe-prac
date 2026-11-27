// Starting Pyodide and running one job in it: a set of tests (runner.browser_tests) or a
// scratch.py (runner.browser_scratch). py-worker.js uses this in a Web Worker; the Node tests in
// tests/js/ use it directly, so both run exactly the same code.

const WORK = "/work"; // the job's files: solution.py, scratch.py, helpers.py
const LIB = "/swe"; // runner.py

// Load Pyodide and the runner. `readText(path)` returns a file of the site (py/runner.py).
export async function startPython(loadPyodide, readText) {
  const [py, runner] = await Promise.all([loadPyodide(), readText("py/runner.py")]);
  py.FS.mkdirTree(LIB);
  py.FS.mkdirTree(WORK);
  py.FS.writeFile(`${LIB}/runner.py`, runner);
  py.runPython(`import sys\nsys.path.insert(0, ${JSON.stringify(LIB)})\nimport runner`);
  return py;
}

// Run `job` and report through post(message):
//   {type: "begin"}                       the files are written and the run starts
//   {type: "event", event}                a runner event (import_error, start, call, end, done...)
//   {type: "stdout" | "stderr", text}     scratch output, as it's printed
//   {type: "finished", exit_code}         the job ended normally (exit_code for scratch)
//   {type: "fatal", message}              Python itself failed (a stack overflow kills it)
// A worker runs one job: user code can leave the interpreter in any state.
export function runJob(py, job, post) {
  try {
    py.FS.writeFile(`${WORK}/solution.py`, job.code);
    for (const [name, text] of Object.entries(job.files ?? {})) py.FS.writeFile(`${WORK}/${name}`, text);
    const runner = py.pyimport("runner");
    post({ type: "begin" });
    if (job.kind === "tests") {
      const payload = JSON.stringify({ tests: job.tests, options: job.options ?? {} });
      runner.browser_tests(`${WORK}/solution.py`, job.className, payload, (text) => {
        post({ type: "event", event: JSON.parse(text) });
      });
      post({ type: "finished", exit_code: 0 });
    } else {
      py.FS.writeFile(`${WORK}/scratch.py`, job.scratch);
      const code = runner.browser_scratch(WORK, "scratch.py",
        (text) => post({ type: "stdout", text }),
        (text) => post({ type: "stderr", text }));
      post({ type: "finished", exit_code: code });
    }
  } catch (err) {
    post({ type: "fatal", message: String(err?.message ?? err) });
  }
}
