// A Web Worker that keeps the tracker's Python loaded, so classifying mail never blocks the page.
// It uses the Pyodide the practice section ships (../practice/vendor/pyodide/), so a browser that
// has practiced already has it cached. Messages: {id, op, payload} in, {id, ok, result | error} out.
import { loadPyodide } from "../practice/vendor/pyodide/pyodide.mjs";
import { callTracker, startTracker } from "./tracker-py.js";

const readText = async (path) => {
  const res = await fetch(new URL(path, import.meta.url));
  if (!res.ok) throw new Error(`Could not load ${path} (${res.status})`);
  return res.text();
};

const api = startTracker(loadPyodide, readText);

onmessage = async ({ data }) => {
  try {
    const result = callTracker(await api, data.op, data.payload);
    postMessage({ id: data.id, ok: true, result });
  } catch (err) {
    postMessage({ id: data.id, ok: false, error: String(err?.message ?? err) });
  }
};
