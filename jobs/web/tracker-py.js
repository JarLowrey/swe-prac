// Starting the tracker's Python (job_tracker.py, gmail_message.py and tracker_api.py) in Pyodide,
// and calling it. tracker-worker.js uses this in a Web Worker; the Node tests in jobs/tests/js/
// use it directly, so both run exactly the same code.

const FILES = ["job_tracker.py", "gmail_message.py", "tracker_api.py"];
const OPS = new Set(["query", "parse", "scan", "prep_context"]);

// `readText(path)` returns a file of the site (py/<name>.py).
export async function startTracker(loadPyodide, readText) {
  const [py, ...texts] = await Promise.all([loadPyodide(), ...FILES.map((f) => readText(`py/${f}`))]);
  py.FS.mkdirTree("/jobs");
  FILES.forEach((f, i) => py.FS.writeFile(`/jobs/${f}`, texts[i]));
  py.runPython('import sys\nsys.path.insert(0, "/jobs")\nimport tracker_api');
  return py.pyimport("tracker_api");
}

// One call: JSON text in, JSON text out (see tracker_api.py).
export function callTracker(api, op, payload) {
  if (!OPS.has(op)) throw new Error(`No tracker function ${op}`);
  return api[op](payload);
}
