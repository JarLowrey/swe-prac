// Shared setup for the JavaScript tests: they run the built site in Node, so what they check is
// exactly what ships. That's site/practice/ at the repo root (from `python build.py`), or
// practice/site/ (from `python tools/build_static.py`), or $SWE_PRAC_SITE.
//
// The browser pieces Node lacks are stood in for here: Web Workers (python.js starts one per
// run; node-worker.mjs gives it the worker's globals over worker_threads) and `window`, which
// python.js tells about Python loading.
import { existsSync, readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Worker as ThreadWorker } from "node:worker_threads";

export const REPO = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const built = (dir) => existsSync(join(dir, "vendor", "pyodide", "pyodide.mjs"));
const candidates = [join(REPO, "..", "site", "practice"), join(REPO, "site")];
export const SITE = resolve(process.env.SWE_PRAC_SITE ?? candidates.find(built) ?? candidates[0]);

if (!built(SITE)) {
  throw new Error(`No built site at ${SITE}. Run: python build.py (at the repo root)`);
}

export const siteUrl = (path) => pathToFileURL(join(SITE, path)).href;
export const readSiteText = (path) => readFile(join(SITE, path), "utf8");
export const readSiteJson = async (path) => JSON.parse(await readSiteText(path));
export const data = JSON.parse(readFileSync(join(SITE, "data.json"), "utf8"));

// A Web Worker on worker_threads: the same onmessage / postMessage / terminate surface.
class NodeWebWorker {
  constructor(url) {
    this.onmessage = null;
    this.onerror = null;
    this.thread = new ThreadWorker(new URL("./node-worker.mjs", import.meta.url), {
      workerData: { url: String(url) },
    });
    this.thread.on("message", (msg) => this.onmessage?.({ data: msg }));
    this.thread.on("error", (err) => this.onerror?.({ message: err.message, preventDefault() {} }));
  }

  postMessage(msg) {
    this.thread.postMessage(msg);
  }

  terminate() {
    this.thread.terminate();
  }
}

globalThis.Worker ??= NodeWebWorker;
globalThis.window ??= new EventTarget();

// The site's modules, imported from site/ (not swe_prac/static/, which has no vendor/ruff).
export const importSite = (path) => import(siteUrl(path));

// python.js's runTests() and runScratch(), ready to call.
export async function python() {
  const mod = await importSite("python.js");
  await mod.warmUp();
  return mod;
}

// ruff, loaded with the module's bytes (Node can't fetch file: URLs).
export async function ruff() {
  const mod = await importSite("lint.js");
  await mod.warmUp(await readFile(join(SITE, "vendor", "ruff", "ruff_wasm_bg.wasm")));
  return mod;
}

// One Pyodide in this thread, for sweeps that run many jobs: runJob() as the worker calls it,
// collecting its messages. Each job reloads solution.py, so jobs don't see each other's code.
export async function inlinePython() {
  const { loadPyodide } = await importSite("vendor/pyodide/pyodide.mjs");
  const { runJob, startPython } = await importSite("py-job.js");
  const py = await startPython(() => loadPyodide(), readSiteText);
  return (job) => {
    const messages = [];
    runJob(py, job, (m) => messages.push(m));
    const fatal = messages.find((m) => m.type === "fatal");
    if (fatal) throw new Error(`Python failed: ${fatal.message}`);
    return messages.filter((m) => m.type === "event").map((m) => m.event);
  };
}
