// gmail.sync() against a fake Gmail and a fake clock: what it downloads, how it paces itself,
// and what it does when Gmail says to slow down, refuses the token or has lost a message.
import assert from "node:assert/strict";
import { test } from "node:test";
import { importSite } from "./harness.mjs";

const { AuthError, sync } = await importSite("jobs/gmail.js");
const API = "https://gmail.googleapis.com/gmail/v1/users/me/";

const json = (status, body, headers = {}) => ({
  ok: status >= 200 && status < 300, status, json: async () => body,
  headers: { get: (k) => headers[k] ?? null },
});

// A fake Gmail holding `ids`, with a clock that only moves when sync() sleeps. `fail(id, n)` may
// return a response for the n-th request for that message instead of the message.
function fakeGmail(ids, { pageSize = 500, fail = () => null } = {}) {
  let t = 0;
  const log = [];
  const tries = new Map();
  const fetchImpl = async (url, opts) => {
    assert.equal(opts.headers.Authorization, "Bearer tok");
    const path = url.slice(API.length);
    log.push({ t, path });
    if (path === "profile") return json(200, { emailAddress: "candidate@example.com" });
    if (path.startsWith("messages?")) {
      const q = new URLSearchParams(path.slice("messages?".length));
      const start = Number(q.get("pageToken") || 0);
      const page = ids.slice(start, start + pageSize).map((id) => ({ id }));
      const next = start + pageSize < ids.length ? { nextPageToken: String(start + pageSize) } : {};
      return json(200, { messages: page, ...next });
    }
    const id = decodeURIComponent(path.match(/^messages\/([^?]+)\?format=raw/)[1]);
    const n = (tries.get(id) ?? 0) + 1;
    tries.set(id, n);
    return fail(id, n) ?? json(200, { id, threadId: id, labelIds: ["INBOX"], internalDate: "0", raw: "" });
  };
  // Sleepers wake one at a time in time order, each once everything else has settled, with the
  // clock set to its wake-up time: concurrent downloads see the times real timers would give.
  const sleepers = [];
  let ticking = false;
  const tick = () => {
    ticking = false;
    sleepers.sort((a, b) => a.at - b.at);
    const s = sleepers.shift();
    if (!s) return;
    t = Math.max(t, s.at);
    s.resolve();
    if (sleepers.length) { ticking = true; setImmediate(tick); }
  };
  const sleep = (ms) => new Promise((resolve) => {
    sleepers.push({ at: t + ms, resolve });
    if (!ticking) { ticking = true; setImmediate(tick); }
  });
  return { fetchImpl, sleep, now: () => t, log, gets: () => log.filter((r) => /^messages\/[^?]+\?/.test(r.path)) };
}

async function run(gmail, extra = {}) {
  const batches = [];
  const progress = [];
  const res = await sync({
    accessToken: "tok", query: "after:2026/10/01", fetchImpl: gmail.fetchImpl, sleep: gmail.sleep, now: gmail.now,
    onBatch: async (batch, account) => { batches.push({ ids: batch.map((m) => m.id), account }); },
    onProgress: (p) => progress.push(p), ...extra,
  });
  return { res, batches, progress };
}

const ids = (n, prefix = "m") => Array.from({ length: n }, (_, i) => `${prefix}${i}`);

test("downloads what isn't stored yet, in batches, across list pages", async () => {
  const gmail = fakeGmail(ids(7), { pageSize: 3 });
  const { res, batches, progress } = await run(gmail, { known: new Set(["m0", "m4"]), batchSize: 2 });
  assert.deepEqual(res, { account: "candidate@example.com", listed: 7, fetched: 5, failed: [], stopped: false });
  assert.deepEqual(batches.flatMap((b) => b.ids).sort(), ["m1", "m2", "m3", "m5", "m6"]);
  assert.ok(batches.every((b) => b.ids.length <= 2 && b.account === "candidate@example.com"));
  assert.equal(gmail.log.filter((r) => r.path.startsWith("messages?")).length, 3); // three list pages
  assert.equal(progress.at(-1).phase, "done");
  assert.equal(progress.at(-1).done, 5);
});

test("stays under the per-minute rate", async () => {
  const gmail = fakeGmail(ids(30));
  await run(gmail, { perMinute: 60, concurrency: 3 });
  const times = gmail.gets().map((r) => r.t).sort((a, b) => a - b);
  assert.equal(times.length, 30);
  for (let i = 1; i < times.length; i++) assert.ok(times[i] - times[i - 1] >= 1000 - 1e-6, `gap ${i}: ${times[i] - times[i - 1]}`);
});

test("waits when Gmail says to slow down, then carries on", async () => {
  const gmail = fakeGmail(ids(3), {
    fail: (id, n) => (id === "m1" && n === 1 ? json(429, {}, { "Retry-After": "30" })
      : id === "m2" && n === 1 ? json(403, { error: { errors: [{ reason: "userRateLimitExceeded" }] } }) : null),
  });
  const { res, progress } = await run(gmail, { concurrency: 1 });
  assert.deepEqual([res.fetched, res.failed], [3, []]);
  assert.ok(progress.some((p) => p.waitingUntil > 0), "reported the wait");
  const m1 = gmail.log.filter((r) => r.path.startsWith("messages/m1?"));
  assert.equal(m1.length, 2);
  assert.ok(m1[1].t - m1[0].t >= 30_000, "honoured Retry-After");
});

test("a refused token stops the sync, after handing over what it had", async () => {
  const gmail = fakeGmail(ids(5), { fail: (id) => (id === "m3" ? json(401, {}) : null) });
  const batches = [];
  await assert.rejects(sync({
    accessToken: "tok", query: "q", fetchImpl: gmail.fetchImpl, sleep: gmail.sleep, now: gmail.now, concurrency: 1,
    onBatch: async (b) => { batches.push(...b.map((m) => m.id)); },
  }), (err) => err instanceof AuthError && /expired/.test(err.message));
  assert.deepEqual(batches, ["m0", "m1", "m2"]);
});

test("a 403 that isn't a rate limit says to check the Gmail API", async () => {
  const gmail = fakeGmail([]);
  const fetchImpl = async (url, opts) => (url.endsWith("/profile") ? json(403, { error: { message: "Gmail API has not been used in project 1 before or it is disabled." } }) : gmail.fetchImpl(url, opts));
  await assert.rejects(run({ ...gmail, fetchImpl }), (err) => err instanceof AuthError && /Gmail API has not been used/.test(err.message));
});

test("a message deleted since it was listed is skipped, not failed", async () => {
  const gmail = fakeGmail(ids(3), { fail: (id) => (id === "m1" ? json(404, {}) : null) });
  const { res, batches } = await run(gmail);
  assert.deepEqual([res.fetched, res.failed], [3, []]); // done counts it; nothing to retry
  assert.deepEqual(batches.flatMap((b) => b.ids).sort(), ["m0", "m2"]);
});

test("a message that keeps failing is listed for the next sync", async () => {
  const gmail = fakeGmail(ids(2), { fail: (id) => (id === "m1" ? json(500, {}) : null) });
  const { res } = await run(gmail);
  assert.deepEqual(res.failed, ["m1"]);
  assert.equal(gmail.log.filter((r) => r.path.startsWith("messages/m1?")).length, 6); // 1 + 5 retries
});

test("Stop ends the downloads and keeps what came in", async () => {
  const gmail = fakeGmail(ids(10));
  const abort = new AbortController();
  const batches = [];
  const res = await sync({
    accessToken: "tok", query: "q", fetchImpl: gmail.fetchImpl, sleep: gmail.sleep, now: gmail.now, concurrency: 1, batchSize: 100,
    signal: abort.signal, onBatch: async (b) => { batches.push(...b.map((m) => m.id)); },
    onProgress: (p) => { if (p.done === 4) abort.abort(); },
  });
  assert.equal(res.stopped, true);
  assert.deepEqual(batches, ["m0", "m1", "m2", "m3"]);
});
