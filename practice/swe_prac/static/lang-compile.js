// A Web Worker that compiles Java or C++ for the page (compilers.js), started as
// lang-compile.js?lang=java or ?lang=cpp. It stays loaded between runs: a compiler takes seconds
// to load. Messages:
//
//   page -> worker   {id, files, main, mode}
//   worker -> page   {type: "ready"} | {type: "boot-error", message} | {type: "progress", text}
//                    {type: "result", id, result} | {type: "error", id, message}
import { createCppCompiler, createJavaCompiler } from "./compilers.js";

const lang = new URL(import.meta.url).searchParams.get("lang");
const site = new URL("./", import.meta.url);

// Files the site serves gzipped, because GitHub Pages compresses only some types on the fly.
const GZIPPED = /\.(tar|pch)$/;

const realFetch = globalThis.fetch.bind(globalThis);
async function fetchFile(input, init) {
  const url = String(input instanceof Request ? input.url : input);
  if (!GZIPPED.test(new URL(url).pathname)) return realFetch(input, init);
  const res = await realFetch(`${url}.gz`, init);
  if (!res.ok) return res;
  return new Response(res.body.pipeThrough(new DecompressionStream("gzip")), {
    headers: { "Content-Type": "application/octet-stream" },
  });
}
// The C++ compiler fetches its own files (llvm-resources.tar among them) with fetch().
globalThis.fetch = fetchFile;

async function fetchOk(path) {
  const res = await fetchFile(new URL(path, site));
  if (!res.ok) throw new Error(`Could not load ${path} (${res.status})`);
  return res;
}
const fetchBytes = async (path) => new Uint8Array(await (await fetchOk(path)).arrayBuffer());
const fetchText = async (path) => (await fetchOk(path)).text();

let lastProgress = 0;
function progress({ doneLength, totalLength }) {
  const now = performance.now();
  if (now - lastProgress < 250 || !totalLength) return;
  lastProgress = now;
  postMessage({ type: "progress", text: `${Math.min(99, Math.round((100 * doneLength) / totalLength))}%` });
}

async function start() {
  if (lang === "java") {
    const { load } = await import("./vendor/java/compiler.wasm-runtime.js");
    return createJavaCompiler({ load, fetchBytes, fetchText });
  }
  const clang = await import("./vendor/clang/bundle.js");
  // Download the compiler's own files first (runClang with no arguments does only that): a real
  // compile wouldn't report the download's progress.
  await clang.runClang(null, {}, { fetchProgress: progress });
  const compiler = await createCppCompiler({ clang, fetchBytes, fetchText });
  // Compile something small now, so the first real compile is as fast as the others.
  await compiler.compile({ files: { "swe_nodes.hpp": "", "warm.cpp": "int main() {}\n" }, main: "warm.cpp", mode: "check" });
  return compiler;
}

const compiler = start();
compiler.then(
  () => postMessage({ type: "ready" }),
  (err) => postMessage({ type: "boot-error", message: String(err?.message ?? err) }),
);

onmessage = async ({ data }) => {
  let c;
  try {
    c = await compiler;
  } catch {
    return; // boot-error was already posted
  }
  try {
    const result = await c.compile(data);
    postMessage({ type: "result", id: data.id, result }, result.wasm ? [result.wasm.buffer] : []);
  } catch (err) {
    postMessage({ type: "error", id: data.id, message: String(err?.message ?? err) });
  }
};
