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

let current = null; // the job the download progress belongs to
const loaded = new Map(); // "model@revision" -> Promise<pipeline>: a session may use both models

function load(model, revision) {
  const key = `${model}@${revision}`;
  if (!loaded.has(key)) {
    const asr = pipeline("automatic-speech-recognition", model, {
      revision,
      device: "wasm",
      dtype: "q8", // the 8-bit weights: a quarter of the download, about the same accuracy
      progress_callback: (p) => {
        if (p.status === "progress_total") self.postMessage({ id: current, type: "load", loaded: p.loaded, total: p.total });
      },
    });
    loaded.set(key, asr);
    asr.catch(() => { if (loaded.get(key) === asr) loaded.delete(key); }); // try again next time
  }
  return loaded.get(key);
}

self.onmessage = async ({ data: { id, model, revision, audio } }) => {
  current = id;
  let asr;
  try {
    asr = await load(model, revision);
  } catch (err) {
    self.postMessage({ id, type: "error", phase: "load", message: String(err?.message ?? err) });
    return;
  }
  if (!audio) { self.postMessage({ id, type: "done", chunks: [] }); return; }
  try {
    const out = await asr(audio, { return_timestamps: true });
    self.postMessage({ id, type: "done", chunks: out.chunks ?? [{ text: out.text, timestamp: [0, null] }] });
  } catch (err) {
    self.postMessage({ id, type: "error", phase: "run", message: String(err?.message ?? err) });
  }
};
