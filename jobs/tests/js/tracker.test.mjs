// The tracker's Python in Pyodide, called the way the page calls it: Gmail API messages in,
// records out (parse), records in, applications out (scan), and the interview-prep context.
import assert from "node:assert/strict";
import { before, test } from "node:test";
import { apiMessage, day, tracker } from "./harness.mjs";

let call;
before(async () => { call = await tracker(); });

const MAIL = [
  apiMessage({ id: "a1", from: '"Acme Jobs" <jobs@acme.example>', subject: "Thank you for applying to Acme",
    body: "We received your application for Backend Engineer at Acme.", when: day(2026, 10, 20) }),
  apiMessage({ id: "a2", thread: "a1", from: "recruiter@acme.example", subject: "Acme interview",
    body: "Thanks for your application. We would like to schedule an interview with you for the Backend Engineer role.",
    when: day(2026, 10, 24) }),
  apiMessage({ id: "f1", from: "friend@example.org", subject: "Lunch", body: "See you at noon? Café at 12 — ok?",
    when: day(2026, 10, 25) }),
];

test("parse turns Gmail's raw messages into records", () => {
  const out = call("parse", { account: "candidate@example.com", messages: MAIL });
  assert.deepEqual(out.errors, []);
  const [a1, a2, f1] = out.messages;
  assert.equal(a1.from, "jobs@acme.example");
  assert.equal(a1.subject, "Thank you for applying to Acme");
  assert.equal(a1.internalDate, day(2026, 10, 20));
  assert.match(a1.body, /We received your application/);
  assert.match(a1.url, /^https:\/\/mail\.google\.com\/mail\/\?authuser=candidate@example\.com#all\/thread-f:\d+$/);
  assert.equal(a2.threadId, "a1");
  assert.match(f1.body, /Café at 12 — ok\?/); // UTF-8 survives base64url and the trip through Python
});

test("parse reports a broken message and keeps the rest", () => {
  const out = call("parse", { messages: [{ id: "x", raw: 5 }, MAIL[0]] });
  assert.equal(out.messages.length, 1);
  assert.match(out.errors[0], /^x: /);
});

test("scan groups the records into applications", () => {
  const { messages } = call("parse", { account: "", messages: MAIL });
  const out = call("scan", { messages, since: "2026-10-01", before: null, settings: { vendor_domains: [], ignore_senders: [] } });
  assert.equal(out.notices, 2);
  assert.equal(out.applications.length, 1);
  const [app] = out.applications;
  assert.deepEqual([app.company, app.position, app.status], ["Acme", "Backend Engineer", "interviewing"]);
  assert.deepEqual(app.notices.map((n) => n.id), ["a1", "a2"]);
});

test("scan applies the settings, and the next call replaces them", () => {
  const { messages } = call("parse", { account: "", messages: MAIL });
  assert.deepEqual(call("scan", { messages, settings: { ignore_senders: ["acme.example"] } }).applications, []);
  assert.equal(call("scan", { messages, settings: {} }).applications.length, 1);
});

test("query builds the Gmail search", () => {
  assert.equal(call("query", { since: "2026-10-20", before: "", everything: true }), "after:2026/10/19 -in:sent -in:drafts");
  const q = call("query", { since: "2026-10-20", before: "2026-11-01", terms: "interview OR offer" });
  // a day's margin each side for time zones; scan applies the exact dates
  assert.match(q, /after:2026\/10\/19/);
  assert.match(q, /before:2026\/11\/02/);
  assert.match(q, /interview OR offer/);
});

test("prep_context has the trail and the emails, without addresses", () => {
  const { messages } = call("parse", { account: "", messages: MAIL });
  const { applications } = call("scan", { messages });
  const text = call("prep_context", { applications, messages });
  assert.match(text, /## Applications at Acme \(1\)/);
  assert.match(text, /Backend Engineer: interviewing/);
  assert.match(text, /schedule an interview/);
  assert.doesNotMatch(text, /See you at noon/);
  assert.doesNotMatch(text, /@/);
});

test("only the four tracker functions can be called", async () => {
  const { importSite } = await import("./harness.mjs");
  const { callTracker } = await importSite("jobs/tracker-py.js");
  assert.throws(() => callTracker({}, "configure", "{}"), /No tracker function configure/);
});
