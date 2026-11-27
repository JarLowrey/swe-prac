// Shared setup for the JavaScript tests: they run the built site in Node, so what they check is
// exactly what ships. That's site/practice/ at the repo root (from `python build.py`), or
// practice/site/ (from `python tools/build_static.py`), or $SWE_PRAC_SITE.
//
// The browser pieces Node lacks are stood in for here: Web Workers (python.js starts one per
// run; node-worker.mjs gives it the worker's globals over worker_threads) and `window`, which
// python.js tells about Python loading.
import { createHash } from "node:crypto";
import {
  copyFileSync, existsSync, linkSync, mkdirSync, readFileSync, readdirSync, renameSync, writeFileSync,
} from "node:fs";
import { readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Worker as ThreadWorker } from "node:worker_threads";
import { gunzipSync } from "node:zlib";

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

// ---------------------------------------------------------------- Java and C++, in this thread
// The site's compilers (compilers.js) and program runner (lang-job.js), on its own toolchains,
// without lang-compile.js's worker: in Node, clang reads its own files from disk, and the site
// has llvm-resources.tar only gzipped (the browser's fetch unzips it). So clang runs here from a
// temp folder with the archive unzipped beside it, kept between runs.
const GZIPPED = /\.(tar|pch)$/; // lang-compile.js serves these as .gz

async function siteBytes(path) {
  if (GZIPPED.test(path)) return new Uint8Array(gunzipSync(await readFile(join(SITE, `${path}.gz`))));
  return new Uint8Array(await readFile(join(SITE, path)));
}

async function clangBundle() {
  const from = join(SITE, "vendor", "clang");
  const version = createHash("sha256").update(readFileSync(join(from, "README.txt"))).digest("hex").slice(0, 12);
  const dir = join(tmpdir(), `swe-prac-clang-${version}`);
  if (!existsSync(join(dir, "llvm-resources.tar"))) {
    mkdirSync(dir, { recursive: true });
    for (const name of readdirSync(from).filter((f) => /\.(js|wasm)$/.test(f))) {
      if (existsSync(join(dir, name))) continue;
      try { linkSync(join(from, name), join(dir, name)); } catch { copyFileSync(join(from, name), join(dir, name)); }
    }
    const partial = join(dir, `llvm-resources.tar.${process.pid}`);
    writeFileSync(partial, gunzipSync(readFileSync(join(from, "llvm-resources.tar.gz"))));
    renameSync(partial, join(dir, "llvm-resources.tar"));
  }
  return import(pathToFileURL(join(dir, "bundle.js")).href);
}

const JAVA_BUILDS_PER_COMPILER = 6; // as compiled.js: the Java compiler grows with each build

/**
 * `language`'s toolchain: compile({files, main, mode}) as compilers.js does, and
 * tests(file, code, tests, level) / scratch(file, code, scratch), which build and run like
 * compiled.js (without its time-limit scaling and watchdogs) and return what the job posted.
 */
export async function toolchain(language) {
  const { createCppCompiler, createJavaCompiler } = await importSite("compilers.js");
  const { runJob } = await importSite("lang-job.js");
  const { load } = await importSite("vendor/java/compiler.wasm-runtime.js");
  const fetchText = (path) => readFile(join(SITE, path), "utf8");
  const clang = language === "cpp" ? await clangBundle() : null;
  let compiler = null;
  let builds = 0;

  async function compile(request) {
    if (!compiler || (language === "java" && builds >= JAVA_BUILDS_PER_COMPILER)) {
      compiler = language === "java"
        ? await createJavaCompiler({ load, fetchBytes: siteBytes, fetchText })
        : await createCppCompiler({ clang, fetchBytes: siteBytes, fetchText });
      builds = 0;
    }
    builds += 1;
    return compiler.compile(request);
  }

  async function runJobMessages(job) {
    const messages = [];
    await runJob({ lang: language, ...job }, (m) => messages.push(m), { loadJava: load });
    return messages;
  }

  const java = language === "java";
  return {
    compile,
    async tests(file, code, tests, level = null) {
      const lang = file.langs[language];
      const harness = level === null ? lang.harness : lang.harness[String(level)];
      const harnessFile = java ? "SweMain.java" : "main.cpp";
      const build = await compile({
        files: { ...lang.files, [lang.file]: code, [harnessFile]: harness },
        main: java ? "SweMain" : "main.cpp",
        mode: "build",
      });
      if (!build.ok) return { build, messages: [], events: [], ends: [] };
      const messages = await runJobMessages({ kind: "tests", wasm: build.wasm, tests, options: file.options, names: lang.names });
      const events = messages.filter((m) => m.type === "event").map((m) => m.event);
      return { build, messages, events, ends: events.filter((e) => e.event === "end") };
    },
    async scratch(file, code, scratch) {
      const lang = file.langs[language];
      const scratchFile = java ? "Scratch.java" : "scratch.cpp";
      const build = await compile({
        files: { ...lang.files, [lang.file]: code, [scratchFile]: scratch },
        main: java ? "Scratch" : "scratch.cpp",
        mode: "build",
      });
      if (!build.ok) return { build, messages: [], out: "" };
      const messages = await runJobMessages({ kind: "scratch", wasm: build.wasm });
      const out = messages.filter((m) => m.type === "stdout" || m.type === "stderr").map((m) => m.text).join("");
      return { build, messages, out, exitCode: messages.find((m) => m.type === "finished")?.exit_code ?? null };
    },
  };
}
