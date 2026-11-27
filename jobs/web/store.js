// Everything the Jobs page keeps, in this browser's IndexedDB (database "swe-prac-jobs"): your
// downloaded mail, the applications found in it, your settings and the statuses you set by hand.
// Nothing is sent anywhere. IndexedDB rather than localStorage because mail can run to megabytes,
// and localStorage (about 5 MB for the whole site) also holds the practice history.
//
//   kv store:        settings, run, apps, overrides, hidden, guides, sort
//   messages store:  one record per email (gmail_message.py's shape), keyed by Gmail's id

const DB_NAME = "swe-prac-jobs";
const VERSION = 1;
let opening = null;

function open() {
  opening ??= new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains("kv")) db.createObjectStore("kv");
      if (!db.objectStoreNames.contains("messages")) db.createObjectStore("messages", { keyPath: "id" });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => { opening = null; reject(req.error ?? new Error("This browser won't open IndexedDB.")); };
  });
  return opening;
}

// Run `body(store)` in one transaction; resolves with what the last request returned, once committed.
async function run(storeName, mode, body) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, mode);
    let result;
    const last = body(tx.objectStore(storeName));
    if (last) last.onsuccess = () => { result = last.result; };
    tx.oncomplete = () => resolve(result);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error ?? new Error("Saving was cancelled (is the disk full?)"));
  });
}

export const getKV = async (key, fallback = null) => (await run("kv", "readonly", (s) => s.get(key))) ?? fallback;
export const setKV = (key, value) => run("kv", "readwrite", (s) => s.put(value, key));

export function putMessages(list) {
  if (!list.length) return Promise.resolve();
  return run("messages", "readwrite", (s) => { let r; for (const m of list) r = s.put(m); return r; });
}
export const allMessages = async () => (await run("messages", "readonly", (s) => s.getAll())) ?? [];
export const messageIds = async () => new Set((await run("messages", "readonly", (s) => s.getAllKeys())) ?? []);
export const countMessages = async () => (await run("messages", "readonly", (s) => s.count())) ?? 0;

export async function clearAll() {
  await run("messages", "readwrite", (s) => s.clear());
  await run("kv", "readwrite", (s) => s.clear());
}

// ---------------------------------------------------------------- export / import
const KV_KEYS = ["settings", "run", "overrides", "hidden", "guides"];

// A backup of everything but the derived applications (they are found again from the mail).
export async function exportAll() {
  const out = { kind: "swe-prac-jobs", version: 1, exported_at: new Date().toISOString() };
  for (const key of KV_KEYS) out[key] = await getKV(key);
  out.messages = await allMessages();
  return out;
}

// Accepts this page's backup, or a bare list of mail records ({messages: [...]} or [...]): the
// old command-line scraper's emails.json has the same shape. Mail is merged by id; a backup's
// settings and hand-set statuses are merged over the ones here. Returns how many emails were new.
export async function importAll(data) {
  const list = Array.isArray(data) ? data : Array.isArray(data?.messages) ? data.messages : null;
  if (!list) throw new Error("No emails in that file. Import a file from Export, or an emails.json.");
  const clean = list.filter((m) => m && typeof m === "object" && typeof m.id === "string" && m.id)
    .map((m) => ({
      id: m.id, threadId: String(m.threadId ?? ""), internalDate: Number(m.internalDate) || 0,
      from: String(m.from ?? ""), subject: String(m.subject ?? ""),
      labels: Array.isArray(m.labels) ? m.labels.map(String) : [], body: String(m.body ?? ""),
      url: String(m.url ?? ""),
    }));
  const known = await messageIds();
  await putMessages(clean);
  if (data?.kind === "swe-prac-jobs") {
    for (const key of ["overrides", "hidden", "guides"]) {
      if (data[key] && typeof data[key] === "object") await setKV(key, { ...(await getKV(key, {})), ...data[key] });
    }
    if (data.settings && typeof data.settings === "object") {
      // the settings already in this browser (its client ID, for one) win over the file's
      await setKV("settings", { ...data.settings, ...(await getKV("settings", {})) });
    }
  }
  return clean.filter((m) => !known.has(m.id)).length;
}
