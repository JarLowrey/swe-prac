// The page's side of tracker-worker.js: py(op, payload) sends a call and resolves with its result.
// The worker starts on the first call (loading Python takes a few seconds, longer the first time,
// when the browser downloads it) and then stays up.

let worker = null;
let seq = 0;
const pending = new Map();

function start() {
  worker = new Worker(new URL("./tracker-worker.js", import.meta.url), { type: "module" });
  worker.onmessage = ({ data }) => {
    const call = pending.get(data.id);
    if (!call) return;
    pending.delete(data.id);
    if (data.ok) call.resolve(JSON.parse(data.result));
    else call.reject(new Error(data.error));
  };
  worker.onerror = (e) => {
    e.preventDefault?.();
    const err = new Error(`Python didn't start: ${e.message || "the worker failed to load"}`);
    for (const call of pending.values()) call.reject(err);
    pending.clear();
    worker.terminate();
    worker = null;
  };
}

export function py(op, payload) {
  if (!worker) start();
  return new Promise((resolve, reject) => {
    const id = ++seq;
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, op, payload: JSON.stringify(payload) });
  });
}
