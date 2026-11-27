// A Web Worker that runs Python for one Run, Submit or Run scratch, then is thrown away.
//
// python.js starts one ahead of time so Pyodide (CPython compiled to WebAssembly) is already
// loaded when you press Run. It posts {type: "ready"} once Python is up, then runs the single job
// it's sent (see py-job.js for the messages). Code that runs too long is stopped by the page
// ending this worker, which is the only way to interrupt it.
import { loadPyodide } from "./vendor/pyodide/pyodide.mjs";
import { runJob, startPython } from "./py-job.js";

const readText = async (path) => {
  const res = await fetch(new URL(path, import.meta.url));
  if (!res.ok) throw new Error(`Could not load ${path} (${res.status})`);
  return res.text();
};

const python = startPython(loadPyodide, readText);
python.then(
  () => postMessage({ type: "ready" }),
  (err) => postMessage({ type: "boot-error", message: String(err?.message ?? err) }),
);

// Set before Python has loaded: a job posted early waits for it instead of being lost.
onmessage = async ({ data: job }) => {
  let py;
  try {
    py = await python;
  } catch {
    return; // boot-error was already posted
  }
  runJob(py, job, (message) => postMessage(message));
};
