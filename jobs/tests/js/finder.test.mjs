// The Job finder's data: reading postings.json from the job-find skill, and the counts its charts draw.
import assert from "node:assert/strict";
import { test } from "node:test";
import { importSite, readJobsText } from "./harness.mjs";

const F = await importSite("jobs/finder-data.js");

const posting = (o = {}) => ({
  id: "linkedin:1", source: "linkedin", url: "https://jobs.example.com/linkedin/1", title: "Backend Engineer",
  company: "Northwind", location: "Denver, CO", workplace: "hybrid", posted: "2026-11-26", posted_text: "1 day ago",
  salary_text: "", salary_min: null, salary_max: null, easy_apply: null, query: "backend engineer",
  first_seen: "2026-11-27", last_seen: "2026-11-27", also_on: [], ...o,
});
const file = (postings, o = {}) => ({ version: 1, updated_at: "2026-11-27T15:00:00Z", searches: [], postings, ...o });

test("a file that isn't postings.json is refused with a reason", () => {
  assert.throws(() => F.readPostingsFile({ messages: [] }), /no postings list/);
  assert.throws(() => F.readPostingsFile(null), /no postings list/);
  assert.throws(() => F.readPostingsFile(file([], { version: 2 })), /version: 2/);
});

test("postings it can't use are dropped, the rest cleaned", () => {
  const { postings } = F.readPostingsFile(file([
    posting(),
    posting(), // same id again
    posting({ id: "monster:1", source: "monster" }),
    posting({ id: "indeed:2", source: "indeed", title: "" }),
    posting({ id: "indeed:3", source: "indeed", url: "javascript:alert(1)", workplace: "moon", posted: "yesterday",
      salary_min: 190000, salary_max: 150000, company: "", also_on: ["linkedin:1", "monster:9", 7] }),
    "junk",
  ]));
  assert.deepEqual(postings.map((p) => p.id), ["linkedin:1", "indeed:3"]);
  const p = postings[1];
  assert.equal(p.url, "");
  assert.equal(p.workplace, "");
  assert.equal(p.posted, "");
  assert.deepEqual([p.salary_min, p.salary_max], [150000, 190000]);
  assert.equal(p.company, "Company not shown");
  assert.deepEqual(p.also_on, ["linkedin:1"]);
  const one = F.readPostingsFile(file([posting({ salary_min: 120000, salary_max: null })])).postings[0];
  assert.deepEqual([one.salary_min, one.salary_max], [120000, 120000]);
});

test("'posted in the last N days' counts back from the day of the last search", () => {
  const ref = F.refDay(file([]));
  assert.equal(ref, "2026-11-27");
  assert.equal(F.refDay({ updated_at: "" }, "2026-12-01"), "2026-12-01");
  const ps = [posting({ id: "a", posted: "2026-11-27" }), posting({ id: "b", posted: "2026-11-25" }),
    posting({ id: "c", posted: "2026-11-20" }), posting({ id: "d", posted: "" })];
  assert.deepEqual(F.filterPostings(ps, { days: 1, ref }).map((p) => p.id), ["a"]);
  assert.deepEqual(F.filterPostings(ps, { days: 3, ref }).map((p) => p.id), ["a", "b"]);
  assert.deepEqual(F.filterPostings(ps, { days: 0, ref }).map((p) => p.id), ["a", "b", "c", "d"]);
});

test("search matches every word across title, company and location", () => {
  const ps = [posting({ id: "a" }), posting({ id: "b", title: "Data Engineer", company: "Contoso", location: "Remote" })];
  assert.deepEqual(F.filterPostings(ps, { q: "engineer denver" }).map((p) => p.id), ["a"]);
  assert.deepEqual(F.filterPostings(ps, { q: "CONTOSO" }).map((p) => p.id), ["b"]);
  assert.deepEqual(F.filterPostings(ps, { source: "indeed" }), []);
  assert.deepEqual(F.filterPostings(ps, { workplace: "hybrid" }).map((p) => p.id), ["a", "b"]);
});

test("postings per day fill the gaps with zeros and stop at the span", () => {
  const rows = F.perDay([posting({ id: "a", posted: "2026-11-24" }), posting({ id: "b", source: "indeed", posted: "2026-11-26" }),
    posting({ id: "c", posted: "2026-11-26" })], "2026-11-27");
  assert.deepEqual(rows, [
    { day: "2026-11-24", linkedin: 1, indeed: 0 }, { day: "2026-11-25", linkedin: 0, indeed: 0 },
    { day: "2026-11-26", linkedin: 1, indeed: 1 }, { day: "2026-11-27", linkedin: 0, indeed: 0 }]);
  const long = F.perDay([posting({ posted: "2026-09-01" })], "2026-11-27", 30);
  assert.equal(long.length, 30);
  assert.equal(long[0].day, "2026-10-29");
  assert.deepEqual(F.perDay([posting({ posted: "" })], "2026-11-27"), []);
});

test("companies group by name the way the tracker does", () => {
  const top = F.topCompanies([posting({ id: "a", company: "Northwind, Inc." }), posting({ id: "b", company: "Northwind" }),
    posting({ id: "c", company: "Contoso" })]);
  assert.deepEqual(top, [{ company: "Northwind, Inc.", count: 2 }, { company: "Contoso", count: 1 }]);
  assert.equal(F.normCompany("The Northwind Company, LLC"), F.normCompany("northwind"));
});

test("pay is binned by the midpoint of each range", () => {
  const bins = F.salaryBins([posting({ id: "a", salary_min: 150000, salary_max: 170000 }),
    posting({ id: "b", salary_min: 205000, salary_max: 215000 }), posting({ id: "c" })]);
  assert.deepEqual(bins, [{ lo: 160000, hi: 180000, count: 1 }, { lo: 180000, hi: 200000, count: 0 }, { lo: 200000, hi: 220000, count: 1 }]);
  assert.deepEqual(F.salaryBins([posting()]), []);
  assert.equal(F.money(152000), "$152K");
});

test("the summary tiles", () => {
  const s = F.summary([posting({ id: "a", posted: "2026-11-27", workplace: "remote", salary_min: 1, salary_max: 2 }),
    posting({ id: "b", workplace: "", company: "Contoso" })], "2026-11-27");
  assert.deepEqual(s, { total: 2, lastDay: 1, companies: 2, withSalary: 1, remote: 1, workplaceStated: 1 });
});

test("the sample the page offers is a postings.json the page reads whole", async () => {
  const raw = JSON.parse(await readJobsText("sample-postings.json"));
  const { postings, searches } = F.readPostingsFile(raw);
  assert.equal(postings.length, raw.postings.length, "every sample posting survives the checks");
  assert.ok(searches.length > 0);
  assert.ok(postings.every((p) => p.url.startsWith("https://") && new URL(p.url).hostname.endsWith("example.com")),
    "sample links go to example.com, never to real postings");
  assert.ok(new Set(postings.map((p) => p.source)).size === 2);
  assert.ok(postings.some((p) => p.salary_min) && postings.some((p) => p.also_on.length));
});
