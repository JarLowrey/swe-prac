// A Web Worker that runs one compiled Java or C++ program (lang-job.js), then is thrown away,
// started as lang-run.js?lang=java or ?lang=cpp. Code that runs too long is stopped by the page
// ending this worker. It posts {type: "ready"} once it can take the job.
import { runJob } from "./lang-job.js";

const lang = new URL(import.meta.url).searchParams.get("lang");
const ready = lang === "java"
  ? import("./vendor/java/compiler.wasm-runtime.js").then((m) => m.load)
  : Promise.resolve(null);
ready.then(
  () => postMessage({ type: "ready" }),
  (err) => postMessage({ type: "boot-error", message: String(err?.message ?? err) }),
);

onmessage = async ({ data: job }) => {
  let loadJava;
  try {
    loadJava = await ready;
  } catch {
    return; // boot-error was already posted
  }
  runJob(job, (message) => postMessage(message), { loadJava });
};
