// Speech to text for transcribe.js, off the page's thread: Whisper, OpenAI's open speech
// recognition model, run by Transformers.js on ONNX Runtime's WebAssembly build (the CPU).
// The model downloads from the Hugging Face Hub the first time and the browser caches it; the
// audio never leaves the browser.
//
// in:  {id, model, revision, audio}   audio: Float32Array, 16 kHz mono, at most 30 s; null only
//                                     loads the model (done with no chunks)
// out: {id, type: "load", loaded, total}   model download, in bytes
//      {id, type: "done", chunks}          Whisper's segments: [{text, timestamp: [start, end]}]
//      {id, type: "error", phase, message} phase: "load" (the model) or "run"

import { env, pipeline } from "./vendor/transformers/transformers.min.js";

env.allowLocalModels = false; // there's no models/ folder on this site: go straight to the Hub
const ortFile = (ext) => new URL(`./vendor/onnxruntime/ort-wasm-simd-threaded.${ext}`, import.meta.url).href;
env.backends.onnx.wasm.wasmPaths = { mjs: ortFile("mjs"), wasm: ortFile("wasm") };

// Transformers.js 4.3.2 works out which files a pipeline needs, and their sizes, under the Hub's
// `main` revision whatever revision it was given. Those cache keys never match, so every load
// asked the Hub about every file again, and a model already in this browser didn't load
// offline. So requests and cache keys under `main`, for a model loaded here, go to the revision
// it's pinned to: once a model is in the browser, it loads with no network at all.
const HUB = "https://huggingface.co/";
const revisions = new Map(); // model id -> its pinned revision
function pinned(url) {
  const href = String(url);
  const parts = href.startsWith(HUB) ? href.slice(HUB.length).match(/^(.+?)\/resolve\/main\/(.*)$/) : null;
  return parts && revisions.has(parts[1]) ? `${HUB}${parts[1]}/resolve/${revisions.get(parts[1])}/${parts[2]}` : url;
}
const hubFetch = env.fetch;
env.fetch = (url, options) => hubFetch(pinned(url), options);
if (globalThis.caches) {
  let cache = null; // the browser's Cache Storage, where Transformers.js keeps downloads
  const open = async () => (cache ??= await caches.open(env.cacheKey));
  env.useCustomCache = true;
  env.customCache = {
    match: async (key) => (await open()).match(pinned(key)),
    put: async (key, response) => (await open()).put(pinned(key), response),
  };
}

// "model@revision" -> Promise<pipeline>, loaded once for the page: a session may use both models.
const loaded = new Map();
// "model@revision" -> ids of the jobs waiting for it to load: each gets its download progress.
const waiting = new Map();

function load(key, model, revision) {
  if (!loaded.has(key)) {
    revisions.set(model, revision);
    const asr = pipeline("automatic-speech-recognition", model, {
      revision,
      device: "wasm",
      dtype: "q8", // the 8-bit weights: a quarter of the download, about the same accuracy
      progress_callback: (p) => {
        if (p.status !== "progress_total") return;
        for (const id of waiting.get(key) ?? []) self.postMessage({ id, type: "load", loaded: p.loaded, total: p.total });
      },
    });
    loaded.set(key, asr);
    asr.catch(() => { if (loaded.get(key) === asr) loaded.delete(key); }); // try again next time
  }
  return loaded.get(key);
}

self.onmessage = async ({ data: { id, model, revision, audio } }) => {
  const key = `${model}@${revision}`;
  if (!waiting.has(key)) waiting.set(key, new Set());
  waiting.get(key).add(id);
  let asr;
  try {
    asr = await load(key, model, revision);
  } catch (err) {
    self.postMessage({ id, type: "error", phase: "load", message: String(err?.message ?? err) });
    return;
  } finally {
    waiting.get(key).delete(id);
  }
  if (!audio) { self.postMessage({ id, type: "done", chunks: [] }); return; }
  try {
    const out = await asr(audio, { return_timestamps: true });
    self.postMessage({ id, type: "done", chunks: out.chunks ?? [{ text: out.text, timestamp: [0, null] }] });
  } catch (err) {
    self.postMessage({ id, type: "error", phase: "run", message: String(err?.message ?? err) });
  }
};
