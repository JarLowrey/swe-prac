// The Job finder's data: checking an imported postings.json (written by the job-find skill's
// postings.py) and the counts its charts draw. No page code here, so the Node tests can check it.

export const SOURCES = { linkedin: "LinkedIn", indeed: "Indeed" };
export const WORKPLACES = { remote: "Remote", hybrid: "Hybrid", onsite: "On-site", "": "Not stated" };

const DAY = /^\d{4}-\d{2}-\d{2}$/;
const https = (u) => (/^https:\/\/[^\s"'<>]+$/i.test(String(u || "")) ? String(u) : "");
const str = (v) => (typeof v === "string" ? v.trim() : "");
const num = (v) => (typeof v === "number" && Number.isFinite(v) && v > 0 ? v : null);
const day = (v) => (DAY.test(str(v)) ? str(v) : "");

// Same idea as the tracker's normCo, so "Northwind, Inc." here matches "Northwind" there.
export const normCompany = (s) => String(s || "").toLowerCase().replace(/[,.]/g, " ")
  .replace(/\b(inc|llc|ltd|corp|corporation|co|company|gmbh|plc|technologies|the)\b/g, "").replace(/[^a-z0-9]/g, "");

// Throws with a message for the person importing; drops postings it can't use rather than failing.
export function readPostingsFile(data) {
  if (!data || typeof data !== "object" || !Array.isArray(data.postings)) {
    throw new Error("That isn't a postings.json from the job-find skill (no postings list).");
  }
  if (data.version !== 1) throw new Error(`Unknown postings.json version: ${data.version}.`);
  const seen = new Set();
  const postings = [];
  for (const p of data.postings) {
    if (!p || typeof p !== "object") continue;
    const id = str(p.id);
    const source = str(p.source);
    if (!id || seen.has(id) || !SOURCES[source] || !str(p.title)) continue;
    seen.add(id);
    const workplace = str(p.workplace);
    let [lo, hi] = [num(p.salary_min), num(p.salary_max)];
    if (lo && hi && lo > hi) [lo, hi] = [hi, lo];
    postings.push({
      id, source, url: https(p.url), title: str(p.title), company: str(p.company) || "Company not shown",
      location: str(p.location), workplace: WORKPLACES[workplace] ? workplace : "",
      posted: day(p.posted), posted_text: str(p.posted_text),
      salary_text: str(p.salary_text), salary_min: lo ?? hi, salary_max: hi ?? lo,
      easy_apply: p.easy_apply === true, query: str(p.query),
      first_seen: day(p.first_seen), last_seen: day(p.last_seen),
      also_on: Array.isArray(p.also_on) ? p.also_on.map(str).filter((x) => SOURCES[x.split(":")[0]]) : [],
    });
  }
  const searches = (Array.isArray(data.searches) ? data.searches : []).filter((s) => s && SOURCES[str(s.source)]).map((s) => ({
    source: str(s.source), query: str(s.query), location: str(s.location), remote: s.remote === true,
    days: num(s.days), url: https(s.url), ran_at: str(s.ran_at), found: Number.isInteger(s.found) ? s.found : null, note: str(s.note),
  }));
  return { postings, searches, updated_at: str(data.updated_at) };
}

// Days are local calendar days (YYYY-MM-DD), compared as dates.
const toDate = (s) => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
export const isoDay = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
export const addDays = (s, n) => { const d = toDate(s); d.setDate(d.getDate() + n); return isoDay(d); };
export const daysBetween = (a, b) => Math.round((toDate(b) - toDate(a)) / 86400000);

// "Posted in the last N days" counts from the day of the last search, so an older file still reads right.
export const refDay = (file, today = isoDay(new Date())) => day(String(file?.updated_at || "").slice(0, 10)) || today;

export function filterPostings(postings, { q = "", source = "all", workplace = "all", days = 0, ref } = {}) {
  const words = q.toLowerCase().split(/\s+/).filter(Boolean);
  const since = days && ref ? addDays(ref, -(days - 1)) : "";
  return postings.filter((p) => (source === "all" || p.source === source)
    && (workplace === "all" || p.workplace === workplace)
    && (!since || (p.posted && p.posted >= since))
    && words.every((w) => `${p.title} ${p.company} ${p.location}`.toLowerCase().includes(w)));
}

export function summary(postings, ref) {
  const stated = postings.filter((p) => p.workplace);
  return {
    total: postings.length,
    lastDay: postings.filter((p) => p.posted && p.posted >= ref).length,
    companies: new Set(postings.map((p) => normCompany(p.company))).size,
    withSalary: postings.filter((p) => p.salary_min).length,
    remote: postings.filter((p) => p.workplace === "remote").length,
    workplaceStated: stated.length,
  };
}

// One entry per day from the oldest posting (at most `span` days back) to ref, zeros included.
export function perDay(postings, ref, span = 30) {
  const dated = postings.filter((p) => p.posted && p.posted <= ref);
  if (!dated.length) return [];
  const oldest = dated.reduce((m, p) => (p.posted < m ? p.posted : m), ref);
  const start = daysBetween(oldest, ref) >= span ? addDays(ref, -(span - 1)) : oldest;
  const rows = [];
  for (let d = start; d <= ref; d = addDays(d, 1)) rows.push({ day: d, linkedin: 0, indeed: 0 });
  const at = new Map(rows.map((r) => [r.day, r]));
  for (const p of dated) if (at.has(p.posted)) at.get(p.posted)[p.source] += 1;
  return rows;
}

export function topCompanies(postings, n = 10) {
  const groups = new Map();
  for (const p of postings) {
    const k = normCompany(p.company) || p.company;
    const g = groups.get(k) ?? { company: p.company, count: 0 };
    g.count += 1;
    groups.set(k, g);
  }
  return [...groups.values()].sort((a, b) => b.count - a.count || a.company.localeCompare(b.company)).slice(0, n);
}

export function workplaceCounts(postings) {
  return Object.keys(WORKPLACES).map((k) => ({ key: k, label: WORKPLACES[k], count: postings.filter((p) => p.workplace === k).length }));
}

// Midpoint of each posting's annual pay, in bins of `size` dollars, empty bins between included.
export function salaryBins(postings, size = 20000) {
  const mids = postings.filter((p) => p.salary_min).map((p) => (p.salary_min + p.salary_max) / 2);
  if (!mids.length) return [];
  const first = Math.floor(Math.min(...mids) / size), last = Math.floor(Math.max(...mids) / size);
  const bins = [];
  for (let i = first; i <= last; i++) bins.push({ lo: i * size, hi: (i + 1) * size, count: 0 });
  for (const m of mids) bins[Math.floor(m / size) - first].count += 1;
  return bins;
}

export const money = (n) => (n >= 1000 ? `$${Math.round(n / 1000)}K` : `$${Math.round(n)}`);
