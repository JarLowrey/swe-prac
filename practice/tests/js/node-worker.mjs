// The inside of harness.mjs's Web Worker stand-in: the globals a module worker has (postMessage,
// onmessage, fetch of the site's own files), then the site's real py-worker.js.
import { readFile } from "node:fs/promises";
import { parentPort, workerData } from "node:worker_threads";

globalThis.postMessage = (msg) => parentPort.postMessage(msg);
globalThis.onmessage = null;
parentPort.on("message", (msg) => globalThis.onmessage?.({ data: msg }));

// Node's fetch has no file: URLs; the worker only fetches files next to itself.
const networkFetch = globalThis.fetch;
globalThis.fetch = async (url) => {
  const target = new URL(url);
  if (target.protocol !== "file:") return networkFetch(url);
  try {
    return new Response(await readFile(target));
  } catch {
    return new Response(null, { status: 404 });
  }
};

await import(workerData.url);
