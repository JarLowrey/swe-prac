// Shared setup for the Jobs JavaScript tests. They import the built site (site/ at the repo root,
// from `python build.py`, or $SWE_PRAC_ROOT_SITE), so what they check is exactly what ships:
// site/jobs/ for the page's modules and the tracker's Python, site/practice/vendor/ for Pyodide.
import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const REPO = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
export const SITE = resolve(process.env.SWE_PRAC_ROOT_SITE ?? join(REPO, "site"));

if (!existsSync(join(SITE, "practice", "vendor", "pyodide", "pyodide.mjs")) || !existsSync(join(SITE, "jobs", "py"))) {
  throw new Error(`No built site at ${SITE}. Run: python build.py`);
}

export const importSite = (path) => import(pathToFileURL(join(SITE, path)).href);
export const readJobsText = (path) => readFile(join(SITE, "jobs", path), "utf8");

// The tracker's Python in this thread, exactly as tracker-worker.js starts it. call(op, payload)
// sends JSON text and parses the JSON text back.
let started = null;
export function tracker() {
  started ??= (async () => {
    const { loadPyodide } = await importSite("practice/vendor/pyodide/pyodide.mjs");
    const { callTracker, startTracker } = await importSite("jobs/tracker-py.js");
    const api = await startTracker(() => loadPyodide(), readJobsText);
    return (op, payload) => JSON.parse(callTracker(api, op, JSON.stringify(payload)));
  })();
  return started;
}

// An email as Gmail's users.messages.get?format=raw returns it: base64url, padding left off.
export function apiMessage({ id, thread = id, from, subject, body, when, labels = ["INBOX"] }) {
  const mime = [
    `From: ${from}`,
    "To: candidate@example.com",
    `Subject: ${subject}`,
    `Date: ${new Date(when).toUTCString()}`,
    "MIME-Version: 1.0",
    'Content-Type: text/plain; charset="utf-8"',
    "Content-Transfer-Encoding: 8bit",
    "",
    body,
    "",
  ].join("\r\n");
  const raw = Buffer.from(mime, "utf8").toString("base64url");
  return { id, threadId: thread, labelIds: labels, internalDate: String(when), raw };
}

export const day = (y, m, d, h = 12) => Date.UTC(y, m - 1, d, h);
