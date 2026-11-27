// The prompts the AI skills page builds for your agent.
import assert from "node:assert/strict";
import { test } from "node:test";
import { importSite } from "./harness.mjs";

const { SKILLS, skill } = await importSite("jobs/prompts.js");

test("every skill has what the page shows", () => {
  assert.deepEqual(SKILLS.map((s) => s.id), ["job-find", "job-apply", "job-answers", "job-contacts", "interview-prep"]);
  for (const s of SKILLS) {
    assert.ok(s.title && s.does && s.fields.length, s.id);
    // job-find runs on its defaults (your profile's roles and locations); the others need input
    assert.equal(s.prompt({}), s.id === "job-find" ? "/job-find" : "", `${s.id} with nothing filled in`);
  }
});

test("the skills that drive a browser are marked as using Chrome", () => {
  assert.deepEqual(SKILLS.filter((s) => s.browser).map((s) => s.id), ["job-find", "job-apply", "job-contacts"]);
});

test("job-apply: one link per line, and a batch command for several", () => {
  const s = skill("job-apply");
  assert.equal(s.prompt({ links: " https://a.example/1 \n\n" }), "/job-apply https://a.example/1");
  assert.equal(s.batch({ links: "https://a.example/1" }), "");
  const v = { links: "https://a.example/1\r\nhttps://b.example/2" };
  assert.equal(s.prompt(v), "/job-apply https://a.example/1\nhttps://b.example/2");
  assert.equal(s.batch(v), "python skills/job-apply/scripts/apply.py run https://a.example/1 https://b.example/2");
});

test("job-answers numbers the questions", () => {
  const s = skill("job-answers");
  assert.equal(s.prompt({ company: "Northwind", role: "Backend Engineer", link: "https://n.example/job",
    questions: "Why us? (500 characters)\n\nA project you're proud of" }),
  "/job-answers Draft answers to these application questions for the Backend Engineer role at Northwind.\n"
    + "Posting: https://n.example/job\n\n1. Why us? (500 characters)\n2. A project you're proud of");
  assert.equal(s.prompt({ questions: "Why us?" }), "/job-answers Draft answers to these application questions.\n\n1. Why us?");
});

test("job-contacts needs the company", () => {
  const s = skill("job-contacts");
  assert.equal(s.prompt({ role: "SRE" }), "");
  assert.equal(s.prompt({ company: "Northwind", role: "SRE", team: "Payments" }),
    "/job-contacts Find people to contact at Northwind about the SRE role.\nTeam: Payments");
});

test("interview-prep adds the tracker's status and the email context", () => {
  const s = skill("interview-prep");
  assert.equal(s.prompt({ company: "Northwind" }), "/interview-prep Northwind\n\nRole: not stated");
  const text = s.prompt({ company: "Northwind", role: "Backend Engineer", status: "interviewing",
    lastDate: "Oct 24, 2026", context: "## Applications at Northwind (1)" });
  assert.match(text, /^\/interview-prep Northwind\n\nRole: Backend Engineer\nStatus: interviewing \(latest email Oct 24, 2026\)\n/);
  assert.match(text, /Keep names, email text, links and ids out of any web search\./);
  assert.ok(text.endsWith("## Applications at Northwind (1)"));
});

test("job-find: only what differs from the defaults goes in the prompt", () => {
  const s = skill("job-find");
  assert.equal(s.prompt({ days: "1", sources: "both", locations: "\n \n" }), "/job-find");
  assert.equal(s.prompt({ keywords: " platform engineer ", locations: "Denver, CO\r\nRemote", days: "7", sources: "indeed" }),
    "/job-find\nKeywords: platform engineer\nLocations: Denver, CO; Remote\nPosted within: 7 days\nSites: Indeed only");
  assert.ok(s.fields.filter((f) => f.kind === "select").every((f) => f.options[0][0] && f.options.length > 1));
});
