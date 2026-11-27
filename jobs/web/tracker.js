// The tracker: sync job mail from Gmail, sort it into applications with job_tracker.py (in the
// browser's Python), and show them: a status strip that filters, applications over time, the flow
// of statuses, and a ledger whose rows open into their email trail. Statuses come from rules, not
// AI; you can set one yourself, hide a row, or hand an application to a Claude skill.

import { AuthError, connect, currentToken, forget, prepare, sync } from "./gmail.js";
import { py } from "./python.js";
import { loadSettings } from "./setup.js";
import { allMessages, getKV, messageIds, putMessages, setKV } from "./store.js";
import { ago, dayOf, esc, fmtDay, fmtFull, isoDay, mount, plural, safeUrl, toast, topnav } from "./ui.js";

export const STATUS = {
  applied: { label: "Applied", c: "--st-applied" },
  referred: { label: "Referred", c: "--st-referred" },
  assessment: { label: "Assessment", c: "--st-assessment" },
  scheduling: { label: "Scheduling", c: "--st-scheduling" },
  paperwork: { label: "Forms", c: "--st-paperwork" },
  pending: { label: "Action needed", c: "--st-pending" },
  interviewing: { label: "Interviewing", c: "--st-interviewing" },
  offer: { label: "Offer", c: "--st-offer" },
  accepted: { label: "Accepted", c: "--st-accepted" },
  rejected: { label: "Rejected", c: "--st-rejected" },
  withdrawn: { label: "Withdrawn", c: "--st-withdrawn" },
  expired: { label: "Expired", c: "--st-expired" },
  unknown: { label: "Unknown", c: "--st-other" },
};
const ATS = { "greenhouse.io": "Greenhouse", "greenhouse-mail.io": "Greenhouse", "lever.co": "Lever", "ashbyhq.com": "Ashby",
  "myworkday.com": "Workday", "myworkdayjobs.com": "Workday", "icims.com": "iCIMS", "smartrecruiters.com": "SmartRecruiters",
  "jobvite.com": "Jobvite", "workablemail.com": "Workable", "linkedin.com": "LinkedIn", "indeedemail.com": "Indeed" };
const ACTION = new Set(["assessment", "scheduling", "paperwork", "pending"]);
const SORTS = {
  attention: { label: "Needs attention first", fwd: "Default order", rev: "Reversed" },
  updated: { label: "Last updated", fwd: "Newest first", rev: "Oldest first" },
  applied: { label: "First email", fwd: "Newest first", rev: "Oldest first" },
  company: { label: "Company", fwd: "A to Z", rev: "Z to A" },
  position: { label: "Position", fwd: "A to Z", rev: "Z to A" },
  status: { label: "Status", fwd: "Earliest stage first", rev: "Latest stage first" },
};
const STAGE = Object.keys(STATUS);

const normStatus = (s) => (STATUS[s] ? s : "unknown");
export const normCo = (s) => String(s || "unknown").toLowerCase().replace(/[,.]/g, " ")
  .replace(/\b(inc|llc|ltd|corp|corporation|co|company|gmbh|plc|technologies|the)\b/g, "").replace(/[^a-z0-9]/g, "") || "unknown";
const normPos = (s) => String(s || "").toLowerCase().replace(/\bsr\b/g, "senior").replace(/[^a-z0-9]/g, "");

// A stable key per application (company + role), so hand-set statuses survive a re-sort.
export function withKeys(apps) {
  const used = new Map();
  return apps.map((a) => {
    let key = `${normCo(a.company)}|${normPos(a.position) || "-"}`;
    const n = (used.get(key) || 0) + 1;
    used.set(key, n);
    if (n > 1) key += `#${n}`;
    return { ...a, status: normStatus(a.status), key };
  });
}

// Sort every downloaded email again with the current settings, and save the applications.
export async function rescan() {
  const [s, messages, run] = [await loadSettings(), await allMessages(), (await getKV("run")) ?? {}];
  const out = await py("scan", { messages, since: s.since, before: s.before || null,
    settings: { vendor_domains: s.vendorDomains, ignore_senders: s.ignoreSenders } });
  const apps = withKeys(out.applications);
  await setKV("apps", apps);
  await setKV("run", { ...run, scanned_at: new Date().toISOString(), messages: messages.length, notices: out.notices,
    since: s.since, before: s.before || "" });
  return apps;
}

// ---------------------------------------------------------------- page state
const view = { filter: "all", query: "", showHidden: false, origin: "all", open: new Set(), sortBy: "attention", sortDir: 1 };
let syncing = null; // {abort, progress} while a sync runs; it carries on if you open another tab
let page = null; // the tracker on screen, if any: {bar(), notice(msg), done(msg)}

// Called straight from the click, so that connect() can still open Google's window.
async function doSync(s, run) {
  if (syncing) return;
  let accessToken;
  try {
    accessToken = await connect(run?.account || "");
  } catch (err) {
    page?.notice(err.message);
    return;
  }
  page?.notice("");
  const abort = new AbortController();
  syncing = { abort, progress: { phase: "listing", listed: 0, todo: 0, done: 0, failed: 0, waitingUntil: 0 } };
  page?.bar();
  let unreadable = 0;
  let message = "";
  try {
    const query = await py("query", { since: s.since, before: s.before || null, terms: s.terms, everything: s.everything });
    const res = await sync({
      accessToken, query, known: await messageIds(), signal: abort.signal,
      onProgress: (p) => { if (syncing) { syncing.progress = p; page?.bar(); } },
      onBatch: async (batch, account) => {
        const out = await py("parse", { account, messages: batch });
        unreadable += out.errors.length;
        await putMessages(out.messages);
      },
    });
    await setKV("run", { ...((await getKV("run")) ?? {}), account: res.account, synced_at: new Date().toISOString(),
      query, listed: res.listed });
    const extra = [res.failed.length && `${plural(res.failed.length, "email")} couldn't be downloaded`,
      unreadable && `${plural(unreadable, "email")} couldn't be read`].filter(Boolean);
    if (res.stopped) message = "Stopped. What was downloaded is kept; sync again to carry on.";
    else if (extra.length) message = `${extra.join("; ")}. Sync again to retry.`;
  } catch (err) {
    if (err?.name === "AbortError") message = "Stopped. What was downloaded is kept; sync again to carry on.";
    else if (err instanceof AuthError) { forget(); message = `${err.message} What was downloaded is kept.`; }
    else message = `Sync failed: ${err.message}`;
  } finally {
    syncing.progress = { ...syncing.progress, phase: "sorting" };
    page?.bar();
    try {
      await rescan();
    } catch (err) {
      message = `Sorting the mail failed: ${err.message}`;
    }
    syncing = null;
    if (page) await page.done(message);
    else if (message) toast(message, "bad");
  }
}

function via(from) {
  const m = String(from || "").toLowerCase().match(/@([^>\s]+)/);
  if (!m) return "";
  for (const k in ATS) if (m[1] === k || m[1].endsWith(`.${k}`)) return ATS[k];
  return "";
}

function decorate(apps, overrides, hidden) {
  return apps.map((a) => {
    const v = { ...a };
    const ov = overrides[a.key];
    v.overridden = !!(ov && STATUS[ov.status] && String(ov.at || "") >= String(a.last_date || ""));
    if (v.overridden) v.status = ov.status;
    v.item = ACTION.has(v.status) ? a.item || "" : "";
    v.hidden = !!hidden[a.key];
    v.via = via(a.notices?.[0]?.from);
    return v;
  });
}

const byText = (a, b) => String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base", numeric: true });
const newest = (a, b, f) => String(b[f] || "").localeCompare(String(a[f] || ""));
function sortApps(list) {
  const { sortBy, sortDir } = view;
  // waiting on you and interviewing first, rejected last
  const group = (a) => (ACTION.has(a.status) || a.status === "interviewing" ? 0 : a.status === "rejected" ? 2 : 1);
  const cmp = {
    attention: (a, b) => group(a) - group(b) || newest(a, b, "last_date"),
    updated: (a, b) => newest(a, b, "last_date"),
    applied: (a, b) => newest(a, b, "first_date"),
    company: (a, b) => byText(a.company, b.company) || byText(a.position, b.position),
    position: (a, b) => (!a.position - !b.position) * sortDir || byText(a.position, b.position) || byText(a.company, b.company),
    status: (a, b) => ((a.status === "unknown") - (b.status === "unknown")) * sortDir || STAGE.indexOf(a.status) - STAGE.indexOf(b.status),
  }[sortBy] || (() => 0);
  return list.sort((a, b) => sortDir * cmp(a, b) || newest(a, b, "last_date") || byText(a.company, b.company));
}

// ---------------------------------------------------------------- the page
export async function renderTracker() {
  const sort = await getKV("sort");
  if (sort && SORTS[sort.by]) Object.assign(view, { sortBy: sort.by, sortDir: sort.dir === -1 ? -1 : 1 });
  const root = mount(`${topnav("tracker")}<main class="page jobs">
    <h1>Application tracker</h1>
    <p class="lead">Your job applications, found in your Gmail by rules in Python (<code>job_tracker.py</code>), each with
      the status from the company's latest email. It runs in this page: your mail goes from Gmail to this browser and
      nowhere else, and no AI reads it.</p>
    <section class="syncbar" id="syncbar"></section>
    <div id="notice" class="callout info" hidden></div>
    <div id="body" class="stack"></div>
  </main>`);
  const $ = (sel) => root.querySelector(sel);
  const state = { settings: await loadSettings(), apps: (await getKV("apps", [])) ?? [], run: (await getKV("run")) ?? null,
    overrides: (await getKV("overrides", {})) ?? {}, hidden: (await getKV("hidden", {})) ?? {}, guides: (await getKV("guides", {})) ?? {} };
  if (state.settings.clientId) prepare(state.settings.clientId).catch((err) => notice(err.message));

  function notice(msg) { const n = $("#notice"); n.textContent = msg || ""; n.hidden = !msg; }

  function renderSyncBar() {
    const { run, settings } = state;
    const bar = $("#syncbar");
    if (syncing) {
      const p = syncing.progress;
      const pct = p.todo ? Math.round((p.done / p.todo) * 100) : 0;
      const left = p.todo - p.done;
      const eta = left > 0 ? ` · about ${Math.max(1, Math.round(left / 90))} min left` : "";
      const wait = p.waitingUntil > Date.now() ? " · Gmail asked to slow down, waiting" : "";
      const what = p.phase === "listing" ? `Searching Gmail… ${p.listed ? plural(p.listed, "match") : ""}`
        : p.phase === "downloading" ? `Downloading ${p.done} of ${plural(p.todo, "new email")}${eta}${wait}` : "Sorting…";
      bar.innerHTML = `<div class="what"><b>${esc(what)}</b><div class="bar"><i style="width:${pct}%"></i></div></div>
        <div class="acts"><button data-stop>Stop</button></div>`;
      return;
    }
    const range = settings.since ? `mail from ${fmtFull(settings.since)}${settings.before ? ` to ${fmtFull(settings.before)}` : " on"}` : "";
    const last = run?.synced_at ? `synced ${new Date(run.synced_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}` : "";
    const counts = run?.messages ? `${plural(run.messages, "email")} downloaded` : "";
    const who = run?.account ? esc(run.account) : "Gmail";
    const head = settings.clientId ? `${plural(state.apps.length, "application")} · ${who}`
      : state.apps.length ? `${plural(state.apps.length, "application")} · Gmail isn't set up yet` : "Gmail isn't set up yet";
    bar.innerHTML = `<div class="what"><b>${head}</b><span>${esc([range, counts, last].filter(Boolean).join(" · "))}</span></div>
      <div class="acts">${settings.clientId
        ? `<button class="primary" data-sync>${currentToken() ? "Sync now" : run?.account ? "Connect and sync" : "Connect Gmail and sync"}</button>`
        : `<a class="button-like primary" href="#/gmail">Set up Gmail</a>`}
        <a class="button-like" href="#/gmail">Settings</a></div>`;
  }

  const me = {
    bar: renderSyncBar,
    notice,
    done: async (msg) => {
      state.apps = (await getKV("apps", [])) ?? [];
      state.run = (await getKV("run")) ?? null;
      render();
      notice(msg);
    },
  };
  page = me;

  async function save(key, value) {
    state[key] = value;
    await setKV(key, value);
    render();
  }

  function render() {
    renderSyncBar();
    const all = sortApps(decorate(state.apps, state.overrides, state.hidden));
    const body = $("#body");
    if (!all.length) {
      body.innerHTML = welcome(state);
      return;
    }
    const visible = all.filter((a) => view.showHidden || !a.hidden);
    const hiddenCount = all.length - all.filter((a) => !a.hidden).length;
    const counts = {};
    for (const a of visible) counts[a.status] = (counts[a.status] || 0) + 1;
    if (view.filter !== "all" && !counts[view.filter]) view.filter = "all";
    const q = view.query;
    const shown = visible.filter((a) => (view.filter === "all" || a.status === view.filter)
      && (!q || `${a.company} ${a.position}`.toLowerCase().includes(q)));
    body.innerHTML = `
      <nav class="strip" aria-label="Filter by status">${strip(visible.length, counts)}</nav>
      <section class="panel chart-panel" aria-label="Applications by date">${chart(shown)}</section>
      <section class="panel sankey-panel" aria-label="How statuses changed">${sankey(shown)}</section>
      <div class="toolbar">
        <input type="search" id="q" placeholder="Search company or position" value="${esc(view.query)}" aria-label="Search company or position">
        <label class="dim">Sort by <select id="sort">${Object.entries(SORTS).map(([k, s]) => `<option value="${k}" ${view.sortBy === k ? "selected" : ""}>${s.label}</option>`).join("")}</select></label>
        <button class="sortdir" id="sortdir" title="${esc(`${SORTS[view.sortBy].label}: ${SORTS[view.sortBy][view.sortDir === 1 ? "fwd" : "rev"].toLowerCase()}. Click to reverse.`)}">${view.sortDir === 1 ? "↓" : "↑"}</button>
        ${hiddenCount ? `<button class="ghost" id="toggle-hidden">${view.showHidden ? "Hide dismissed" : `Show ${hiddenCount} dismissed`}</button>` : ""}
      </div>
      <section class="ledger" aria-label="Applications">${shown.length ? ledger(shown, state) : `<div class="empty-state"><strong>Nothing matches</strong><p>Try a different search or status.</p></div>`}</section>
      <p class="foot dim small">Statuses come from rules in <code>job_tracker.py</code>, not AI, and rules can be wrong:
        open an application to set its status yourself. ${state.run?.notices != null ? `${plural(state.run.notices, "email")} of ${state.run.messages} read as application notices.` : ""}</p>`;
  }

  // ---------------------------------------------------------------- events
  root.addEventListener("click", (e) => {
    const t = e.target;
    if (t.closest("[data-sync]")) return void doSync(state.settings, state.run);
    if (t.closest("[data-stop]")) return void syncing?.abort.abort();
    const f = t.closest("[data-f]");
    if (f) { view.filter = f.dataset.f; return render(); }
    const o = t.closest("[data-o]");
    if (o) { view.origin = o.dataset.o; return render(); }
    if (t.closest("#sortdir")) return setSort(view.sortBy, -view.sortDir);
    const sh = t.closest("[data-sort]");
    if (sh) return setSort(sh.dataset.sort, view.sortBy === sh.dataset.sort ? -view.sortDir : 1);
    if (t.closest("#toggle-hidden")) { view.showHidden = !view.showHidden; return render(); }
    const appEl = t.closest(".app");
    if (!appEl) return;
    const key = appEl.dataset.key;
    if (t.closest(".summary")) { view.open.has(key) ? view.open.delete(key) : view.open.add(key); return render(); }
    if (t.closest('[data-act="hide"]')) {
      const hidden = { ...state.hidden };
      if (hidden[key]) delete hidden[key]; else hidden[key] = true;
      return save("hidden", hidden);
    }
    if (t.closest('[data-act="guide-save"]')) {
      const app = state.apps.find((a) => a.key === key);
      const input = appEl.querySelector("[data-guide]");
      const url = input.value.trim();
      if (url && !safeUrl(url)) return toast("Paste a link that starts with https://", "bad");
      const guides = { ...state.guides };
      if (url) guides[normCo(app.company)] = url; else delete guides[normCo(app.company)];
      return save("guides", guides);
    }
  });
  root.addEventListener("change", (e) => {
    if (e.target.id === "sort") return setSort(e.target.value, 1);
    const sel = e.target.closest('[data-act="override"]');
    if (!sel) return;
    const key = sel.closest(".app").dataset.key;
    const app = state.apps.find((a) => a.key === key);
    const overrides = { ...state.overrides };
    if (sel.value) overrides[key] = { status: sel.value, at: app.last_date }; else delete overrides[key];
    save("overrides", overrides);
  });
  root.addEventListener("input", (e) => {
    if (e.target.id !== "q") return;
    view.query = e.target.value.trim().toLowerCase();
    render();
    const q = root.querySelector("#q");
    q.focus();
    q.setSelectionRange(q.value.length, q.value.length);
  });
  function setSort(by, dir) {
    Object.assign(view, { sortBy: by, sortDir: dir });
    setKV("sort", { by, dir });
    render();
  }

  render();
  return () => { if (page === me) page = null; }; // a running sync carries on without the page
}

// ---------------------------------------------------------------- pieces
function welcome({ settings, run }) {
  const steps = settings.clientId
    ? `<p>Gmail is set up. <strong>Connect and sync</strong> above downloads the job mail since
        ${esc(fmtFull(settings.since))} (change it in Settings) and sorts it into applications. The first sync takes
        about a minute per hundred emails; later ones only fetch what's new.</p>`
    : `<p>Two steps: <a href="#/gmail">set up Gmail access</a> once (a Google Cloud project of your own, about ten
        minutes), then connect and sync from here.</p>`;
  return `<div class="panel empty-state">
    <strong>${run?.synced_at ? "No applications found in that mail yet" : "No applications yet"}</strong>
    ${steps}
    <p class="dim small">Have an export from another browser? Import it on the <a href="#/gmail">Connect Gmail</a> page.</p>
  </div>`;
}

function strip(total, counts) {
  let h = `<button class="chipf" data-f="all" aria-pressed="${view.filter === "all"}"><span>All</span><span class="n">${total}</span></button>`;
  for (const k of STAGE) {
    if (counts[k]) h += `<button class="chipf" data-f="${k}" aria-pressed="${view.filter === k}"><span class="dot" style="--c:var(${STATUS[k].c})"></span><span>${STATUS[k].label}</span><span class="n">${counts[k]}</span></button>`;
  }
  return h;
}

function sortHead(by, label) {
  const on = view.sortBy === by;
  const arrow = on ? (view.sortDir === 1 ? "↓" : "↑") : "↕";
  return `<button class="sorth" data-sort="${by}" aria-pressed="${on}">${label}<span class="arr" aria-hidden="true">${arrow}</span></button>`;
}

function ledger(shown, state) {
  let h = `<div class="lhead"><span>${sortHead("company", "Company")} · ${sortHead("position", "Position")}</span><span>${sortHead("status", "Status")}</span><span>Latest email</span><span class="right">${sortHead("updated", "Updated")}</span></div>`;
  for (const a of shown) {
    const st = STATUS[a.status];
    const isOpen = view.open.has(a.key);
    const last = a.notices[a.notices.length - 1] || {};
    const guide = safeUrl(state.guides[normCo(a.company)]);
    h += `<div class="app" data-key="${esc(a.key)}">
      <button class="summary" aria-expanded="${isOpen}">
        <span class="who"><span class="co">${esc(a.company)}</span>${a.via ? ` <span class="via">via ${esc(a.via)}</span>` : ""}<span class="pos">${esc(a.position || "Position not stated")}</span>${guide ? '<span class="prep-tag">Study guide</span>' : ""}</span>
        <span class="statuscell"><span class="chip st" style="--c:var(${st.c})"><span class="dot"></span>${st.label}</span>${a.item ? `<span class="item">${esc(a.item)}</span>` : ""}${a.overridden ? '<span class="ovr">set by you</span>' : ""}</span>
        <span class="detail">${esc(a.last_notification || last.evidence || "")}<span class="subj">${esc(a.last_subject || last.subject || "")}</span></span>
        <span class="when mono"><b>${esc(fmtDay(a.last_date))}</b>${esc(ago(a.last_date))}</span>
      </button>
      ${isOpen ? trail(a, state, guide) : ""}
    </div>`;
  }
  return h;
}

function trail(a, state, guide) {
  let li = "";
  for (const e of a.notices.slice().reverse()) {
    const st = STATUS[e.status] || STATUS.unknown;
    const url = safeUrl(e.url);
    li += `<li><span class="d mono">${esc(fmtFull(e.date))}</span>
      <span class="c"><span class="chip st" style="--c:var(${st.c})"><span class="dot"></span>${st.label}</span></span>
      <span class="t">${esc(e.evidence || "")}<span class="s">${esc(e.subject || "")}${e.from ? ` · ${esc(e.from)}` : ""}</span></span>
      ${url ? `<a href="${esc(url)}" target="_blank" rel="noopener">Open in Gmail</a>` : "<span></span>"}</li>`;
  }
  const cur = a.overridden ? state.overrides[a.key].status : "";
  const opts = [`<option value="">Automatic (from the latest email)</option>`,
    ...STAGE.map((k) => `<option value="${k}" ${cur === k ? "selected" : ""}>${STATUS[k].label}</option>`)].join("");
  const sid = `ovr-${a.key.replace(/[^a-z0-9]/gi, "_")}`;
  const params = (skill) => `#/skills/${skill}?${new URLSearchParams({ app: a.key, company: a.company, role: a.position || "" })}`;
  return `<div class="trail"><ul class="tl">${li}</ul>
    <div class="edit"><label for="${sid}">Status</label><select id="${sid}" data-act="override">${opts}</select>
      <button data-act="hide">${a.hidden ? "Restore to list" : "Not a job application"}</button></div>
    <p class="dim small">A status you set holds until a newer email about this application arrives.</p>
    <div class="handoff"><span class="lbl">With Claude</span>
      <a class="button-like" href="${esc(params("interview-prep"))}">Interview prep prompt</a>
      <a class="button-like" href="${esc(params("job-contacts"))}">Find contacts prompt</a>
      <a class="button-like" href="${esc(params("job-answers"))}">Draft answers prompt</a></div>
    <div class="handoff"><span class="lbl">Study guide</span>
      ${guide ? `<a class="button-like primary" href="${esc(guide)}" target="_blank" rel="noopener">Open</a>` : ""}
      <input type="url" data-guide placeholder="Paste the guide's link once interview-prep has written it" value="${esc(guide)}">
      <button data-act="guide-save">Save link</button></div>
  </div>`;
}

function chart(apps) {
  const counts = new Map();
  for (const a of apps) {
    const key = a.first_date || a.last_date;
    if (/^\d{4}-\d{2}-\d{2}$/.test(key || "")) counts.set(key, (counts.get(key) || 0) + 1);
  }
  const head = (sub) => `<div class="chart-head"><h2>Applications over time</h2><p>${esc(sub)}</p></div>`;
  if (!counts.size) return `${head("No dates match these filters")}<div class="chart-empty">No dates to chart</div>`;
  const keys = [...counts.keys()].sort();
  const dates = [];
  for (let d = dayOf(keys[0]), end = dayOf(keys[keys.length - 1]); d <= end; d.setDate(d.getDate() + 1)) {
    const key = isoDay(d);
    dates.push({ key, count: counts.get(key) || 0 });
  }
  const max = Math.max(...dates.map((d) => d.count), 1);
  const width = 720, height = 220, left = 34, right = 16, top = 28, bottom = 38;
  const plotW = width - left - right, plotH = height - top - bottom;
  const step = plotW / Math.max(dates.length, 1), barW = Math.min(52, step * 0.62);
  const ticks = Math.min(max, 5);
  let svg = `<svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Applications by the date of their first email">`;
  for (let i = 0; i <= ticks; i++) {
    const v = Math.round((i / ticks) * max);
    const y = top + plotH - (v / max) * plotH;
    svg += `<line class="chart-grid" x1="${left}" y1="${y}" x2="${width - right}" y2="${y}"></line><text x="${left - 8}" y="${y + 4}" text-anchor="end">${v}</text>`;
  }
  const labelStep = Math.max(1, Math.ceil(dates.length / 8));
  dates.forEach((d, i) => {
    const barH = (d.count / max) * plotH;
    const x = left + i * step + (step - barW) / 2;
    const y = top + plotH - barH;
    const title = d.count ? `<title>${plural(d.count, "application")} on ${esc(fmtFull(d.key))}</title>` : "";
    svg += `<rect class="chart-bar" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barW.toFixed(1)}" height="${barH.toFixed(1)}" rx="3">${title}</rect>`;
    if (d.count && dates.length <= 40) svg += `<text class="chart-value" x="${(x + barW / 2).toFixed(1)}" y="${Math.max(top + 10, y - 7).toFixed(1)}">${d.count}</text>`;
    if (i % labelStep === 0 || i === dates.length - 1) svg += `<text class="chart-date" x="${(x + barW / 2).toFixed(1)}" y="${height - 12}">${esc(fmtDay(d.key))}</text>`;
  });
  return `${head(`${plural(apps.length, "application")} across ${plural(dates.length, "day")}, by the date of the first email`)}${svg}</svg>`;
}

// In the flow diagram the same status reads "Other" where an application started and "Unknown" where it stands now.
const flowLabel = (s) => (s === "no-update" ? "No update" : STATUS[s]?.label || s);
const statusColor = (s) => (s === "no-update" ? "var(--text-faint)" : `var(${(STATUS[s] || STATUS.unknown).c})`);
// Both "applied" and "referred" start an application; a referral anywhere in the trail marks it as referred.
const originOf = (a) => ((a.notices || []).some((n) => n.status === "referred") || a.status === "referred" ? "referred" : "applied");

function sankey(allApps) {
  const originCounts = { applied: 0, referred: 0 };
  for (const a of allApps) originCounts[originOf(a)]++;
  if (view.origin !== "all" && !originCounts[view.origin]) view.origin = "all";
  const filter = (originCounts.applied && originCounts.referred) || view.origin !== "all"
    ? `<nav class="strip small-strip"><span class="dim small">Started as</span>${[["all", "All", allApps.length], ["applied", "Applied", originCounts.applied], ["referred", "Referred", originCounts.referred]]
      .filter(([k, , n]) => k === "all" || n)
      .map(([k, label, n]) => `<button class="chipf" data-o="${k}" aria-pressed="${view.origin === k}">${k === "all" ? "" : `<span class="dot" style="--c:var(${STATUS[k].c})"></span>`}<span>${label}</span><span class="n">${n}</span></button>`).join("")}</nav>`
    : "";
  const apps = view.origin === "all" ? allApps : allApps.filter((a) => originOf(a) === view.origin);

  // Each path starts at Applied (or Referred) and follows every change of status. "Unknown" emails say
  // nothing about the status, and tasks that arrived after a rejection don't reopen it, so both are
  // skipped. A status you set yourself ends the path.
  const pathOf = (a) => {
    const notices = (a.notices || []).filter((n) => STATUS[n.status] && n.status !== "unknown" && !n.superseded)
      .slice().sort((x, y) => String(x.date).localeCompare(String(y.date)));
    const path = [];
    for (const n of notices) if (path[path.length - 1] !== n.status) path.push(n.status);
    if (a.status !== "unknown" && path[path.length - 1] !== a.status) path.push(a.status);
    if (path[0] !== "applied" && path[0] !== "referred") path.unshift("applied");
    if (path.length === 1) path.push("no-update");
    return path;
  };
  const paths = apps.map(pathOf);
  const head = `<h2>How statuses changed</h2>${filter}`;
  if (!paths.length) return `${head}<div class="chart-empty">No status flow to show</div>`;

  const ORDER = ["referred", "applied", "assessment", "scheduling", "paperwork", "pending", "interviewing", "offer", "accepted", "expired", "withdrawn", "rejected", "no-update"];
  const rankOf = (s) => { const i = ORDER.indexOf(s); return i < 0 ? ORDER.length : i; };
  const cols = Math.max(...paths.map((p) => p.length));
  const nodes = new Map();
  const linkMap = new Map();
  const nodeAt = (col, status) => {
    const id = `${col}|${status}`;
    if (!nodes.has(id)) nodes.set(id, { col, status, in: 0, out: 0, outLinks: [], inLinks: [] });
    return nodes.get(id);
  };
  for (const p of paths) {
    nodeAt(0, p[0]);
    for (let i = 0; i < p.length - 1; i++) {
      const s = nodeAt(i, p[i]), t = nodeAt(i + 1, p[i + 1]);
      const id = `${i}|${p[i]}|${p[i + 1]}`;
      if (!linkMap.has(id)) { const l = { source: s, target: t, value: 0 }; linkMap.set(id, l); s.outLinks.push(l); t.inLinks.push(l); }
      linkMap.get(id).value++;
      s.out++;
      t.in++;
    }
  }
  const links = [...linkMap.values()];
  const value = (n) => Math.max(n.in, n.out);
  const width = 900, nodeWidth = 14, padL = 8, padR = 128, plotTop = 34, gap = 14, minH = 4;
  const total = paths.length;
  const byCol = Array.from({ length: cols }, (_, c) => [...nodes.values()].filter((n) => n.col === c).sort((x, y) => rankOf(x.status) - rankOf(y.status)));
  const maxNodes = Math.max(...byCol.map((c) => c.length));
  const px = Math.max(0.5, Math.min(10, (300 - gap * (maxNodes - 1)) / total));
  const colX = (c) => padL + (cols === 1 ? 0 : (c * (width - padL - padR - nodeWidth)) / (cols - 1));
  let bottomY = plotTop;
  for (const col of byCol) {
    let y = plotTop;
    for (const n of col) {
      n.x = colX(n.col); n.y = y; n.h = Math.max(minH, value(n) * px);
      y += Math.max(n.h, 16) + gap;
    }
    bottomY = Math.max(bottomY, y - gap);
  }
  // stack ribbons inside each node in the order of the node they lead to, so they cross as little as possible
  for (const n of nodes.values()) {
    n.outLinks.sort((a, b) => a.target.y - b.target.y);
    n.inLinks.sort((a, b) => a.source.y - b.source.y);
    let o = n.y; for (const l of n.outLinks) { l.sy = o; o += l.value * px; }
    let i = n.y; for (const l of n.inLinks) { l.ty = i; i += l.value * px; }
  }
  let svg = `<svg viewBox="0 0 ${width} ${Math.ceil(bottomY + 12)}" role="img" aria-label="Application status flow across ${cols} steps">`;
  for (let c = 0; c < cols; c++) svg += `<text class="sankey-label" x="${colX(c)}" y="14" font-size="11">${c === 0 ? "Start" : `Step ${c + 1}`}</text>`;
  const maxValue = Math.max(...links.map((l) => l.value), 1);
  for (const l of links) {
    const x0 = l.source.x + nodeWidth, x1 = l.target.x, xm = (x0 + x1) / 2, w = l.value * px;
    const opacity = 0.3 + 0.35 * (l.value / maxValue);
    svg += `<path d="M ${x0} ${l.sy} C ${xm} ${l.sy}, ${xm} ${l.ty}, ${x1} ${l.ty} L ${x1} ${l.ty + w} C ${xm} ${l.ty + w}, ${xm} ${l.sy + w}, ${x0} ${l.sy + w} Z" fill="${statusColor(l.target.status)}" fill-opacity="${opacity.toFixed(2)}"><title>${esc(flowLabel(l.source.status))} → ${esc(flowLabel(l.target.status))}: ${l.value}</title></path>`;
  }
  for (const n of nodes.values()) {
    const label = n.col === 0 && n.status === "unknown" ? "Other" : flowLabel(n.status);
    svg += `<rect x="${n.x}" y="${n.y}" width="${nodeWidth}" height="${n.h}" rx="3" fill="${statusColor(n.status)}"><title>${esc(label)}: ${value(n)}</title></rect>`;
    svg += `<text x="${n.x + nodeWidth + 6}" y="${n.y + Math.max(n.h, 12) / 2 + 4}" class="sankey-text">${esc(label)} <tspan class="sankey-label">${value(n)}</tspan></text>`;
  }
  const moved = paths.filter((p) => p[1] !== "no-update").length;
  return `${head}<p class="dim small">${plural(total, "application")}, ${moved} with at least one change of status. Each column is the next change; "No update" means nothing came after the application.</p>${svg}</svg>`;
}
