// Job finder: the postings the job-find skill saved to postings.json, imported into this browser
// and charted: postings per day by source, the companies posting most, advertised pay, and a
// table that hands any posting to the job-apply prompt. The skill does the searching; this page
// only reads its file.

import {
  SOURCES, WORKPLACES, filterPostings, money, normCompany, perDay, readPostingsFile, refDay, salaryBins,
  summary, topCompanies, workplaceCounts,
} from "./finder-data.js";
import { getKV, setKV } from "./store.js";
import { ago, esc, fmtDay, fmtFull, mount, plural, toast, topnav } from "./ui.js";

// Series colours, checked for colour-blind separation on the panel surface.
const COLOR = { linkedin: "#4f8cff", indeed: "#e07a35" };
const DAY_OPTIONS = [[0, "Any time"], [1, "Last day"], [3, "Last 3 days"], [7, "Last week"], [14, "Last 2 weeks"]];
const view = { q: "", source: "all", workplace: "all", days: 0 }; // kept while the page is open
let onResize = null;

// Returns a cleanup for the router.
export async function renderFinder() {
  if (onResize) removeEventListener("resize", onResize);
  onResize = null;
  const stored = await getKV("finder");
  const apps = (await getKV("apps", [])) ?? [];
  const tracked = new Set(apps.map((a) => normCompany(a.company)));
  const root = mount(`${topnav("finder")}<main class="page jobs">
    <h1>Job finder</h1>
    <p class="lead">Recent LinkedIn and Indeed postings found by the <a href="#/skills/job-find">Find open positions</a>
      skill. Import its <code>postings.json</code>; it stays in this browser.</p>
    <div class="actions">
      <label class="button-like primary">Import postings.json<input type="file" id="import-postings" accept=".json,application/json" hidden></label>
      <button data-sample>Load sample</button>
      ${stored ? "<button data-clear>Clear</button>" : ""}
    </div>
    <div id="finder-body" class="stack"></div>
    <div class="viz-tip" role="tooltip" hidden></div>
  </main>`);
  const body = root.querySelector("#finder-body");
  const tip = root.querySelector(".viz-tip");

  const save = async (file, name, sample) => {
    await setKV("finder", { file, name, sample, imported_at: new Date().toISOString() });
    Object.assign(view, { q: "", source: "all", workplace: "all", days: 0 });
    return renderFinder();
  };
  root.querySelector("#import-postings").onchange = async (e) => {
    const f = e.target.files[0];
    e.target.value = "";
    if (!f) return;
    try {
      const file = readPostingsFile(JSON.parse(await f.text()));
      await save(file, f.name, false);
      toast(`Imported ${plural(file.postings.length, "posting")}.`, "good");
    } catch (err) {
      toast(err instanceof SyntaxError ? "That file isn't JSON." : err.message, "bad");
    }
  };
  root.querySelector("[data-sample]").onclick = async () => {
    try {
      const res = await fetch("sample-postings.json", { cache: "no-cache" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await save(readPostingsFile(await res.json()), "sample", true);
    } catch (err) {
      toast(`Couldn't load the sample: ${err.message}`, "bad");
    }
  };
  root.querySelector("[data-clear]")?.addEventListener("click", async () => {
    if (!confirm("Remove the imported postings from this browser?")) return;
    await setKV("finder", null);
    renderFinder();
  });

  if (!stored?.file?.postings?.length) {
    body.innerHTML = `<div class="panel empty-state"><strong>No postings yet</strong>
      <p>Run <a href="#/skills/job-find">Find open positions</a> with your AI agent, then import the
        <code>postings.json</code> it writes. Or load the sample to see the charts.</p></div>`;
    return;
  }

  const { file } = stored;
  const ref = refDay(file);
  const draw = () => {
    const shown = filterPostings(file.postings, { ...view, ref });
    // Charts are drawn at their on-screen width (panel padding is 20px a side; two columns above 760px).
    const full = Math.max(280, body.clientWidth - 42);
    const half = innerWidth > 760 ? Math.max(280, (body.clientWidth - 12) / 2 - 42) : full;
    body.innerHTML = `
      ${stored.sample ? '<div class="callout info">Sample data from fictional companies. Import your own postings.json to replace it.</div>' : ""}
      <p class="dim small">Last search ${esc(fmtFull(ref))} · ${file.searches.length} ${file.searches.length === 1 ? "search" : "searches"} ·
        ${plural(file.postings.length, "posting")} in the file</p>
      ${filters(file.postings, ref)}
      ${kpis(shown, ref)}
      <section class="panel chart-panel">${dayChart(shown, ref, full)}</section>
      <div class="two-col">
        <section class="panel">${companyBars(shown)}</section>
        <section class="panel">${salaryChart(shown, half)}</section>
      </div>
      ${table(shown, tracked)}
      ${searchesRun(file.searches)}`;
  };
  draw();

  // Filters: chips and the posted-within menu redraw everything; the search box keeps its focus.
  body.addEventListener("click", (e) => {
    const chip = e.target.closest("[data-filter]");
    if (chip) {
      view[chip.dataset.filter] = chip.dataset.value;
      return draw();
    }
    const co = e.target.closest("[data-company]");
    if (co) {
      view.q = view.q === co.dataset.company ? "" : co.dataset.company;
      draw();
      body.querySelector("#finder-q")?.focus();
    }
  });
  body.addEventListener("change", (e) => {
    if (e.target.id === "finder-days") { view.days = Number(e.target.value); draw(); }
  });
  body.addEventListener("input", (e) => {
    if (e.target.id !== "finder-q") return;
    view.q = e.target.value;
    draw();
    const q = body.querySelector("#finder-q");
    q.focus();
    q.setSelectionRange(q.value.length, q.value.length);
  });

  // One tooltip for every chart mark: anything with data-tip.
  body.addEventListener("pointermove", (e) => {
    const t = e.target.closest("[data-tip]");
    if (!t) { tip.hidden = true; return; }
    tip.textContent = t.dataset.tip;
    tip.hidden = false;
    const x = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8);
    const y = e.clientY + 16 + tip.offsetHeight > innerHeight ? e.clientY - tip.offsetHeight - 10 : e.clientY + 16;
    tip.style.transform = `translate(${x}px, ${y}px)`;
  });
  body.addEventListener("pointerleave", () => { tip.hidden = true; });

  let wide = body.clientWidth;
  onResize = () => { if (Math.abs(body.clientWidth - wide) > 24) { wide = body.clientWidth; draw(); } };
  addEventListener("resize", onResize);
  return () => { removeEventListener("resize", onResize); onResize = null; };
}

// ---------------------------------------------------------------- pieces

function chips(name, options) {
  return options.map(([value, label, n, color]) => `<button class="chipf" data-filter="${name}" data-value="${esc(value)}"
    aria-pressed="${String(view[name]) === String(value)}">${color ? `<span class="dot" style="--c:${color}"></span>` : ""}<span>${esc(label)}</span>${n == null ? "" : `<span class="n">${n}</span>`}</button>`).join("");
}

function filters(all, ref) {
  const inWindow = filterPostings(all, { days: view.days, ref });
  const bySource = Object.keys(SOURCES).map((k) => [k, SOURCES[k], inWindow.filter((p) => p.source === k).length, COLOR[k]]);
  const byPlace = workplaceCounts(inWindow).filter((w) => w.count).map((w) => [w.key, w.label, w.count]);
  return `<div class="finder-filters">
    <div class="toolbar">
      <input type="search" id="finder-q" placeholder="Search title, company or location" value="${esc(view.q)}" aria-label="Search postings">
      <label class="dim">Posted <select id="finder-days">${DAY_OPTIONS.map(([d, l]) => `<option value="${d}" ${view.days === d ? "selected" : ""}>${l}</option>`).join("")}</select></label>
    </div>
    <nav class="strip" aria-label="Filter by source">${chips("source", [["all", "All sources", inWindow.length], ...bySource])}</nav>
    <nav class="strip" aria-label="Filter by workplace">${chips("workplace", [["all", "Any workplace"], ...byPlace])}</nav>
  </div>`;
}

function kpis(shown, ref) {
  const s = summary(shown, ref);
  const pct = (n, d) => (d ? `${Math.round((n / d) * 100)}%` : "–");
  const tile = (label, value, sub = "") => `<div class="kpi"><span class="kpi-label">${label}</span><b>${value}</b>${sub ? `<span class="kpi-sub">${sub}</span>` : ""}</div>`;
  return `<div class="kpi-row">
    ${tile("Postings", s.total)}
    ${tile("Posted in the last day", s.lastDay, `by ${esc(fmtFull(ref))}`)}
    ${tile("Companies", s.companies)}
    ${tile("List pay", pct(s.withSalary, s.total), `${s.withSalary} of ${s.total}`)}
    ${tile("Remote", pct(s.remote, s.workplaceStated), `of ${s.workplaceStated} that say`)}
  </div>`;
}

// A bar with rounded data-end corners (top for columns, right for rows), square on the baseline.
function topRounded(x, y, w, h, r) {
  r = Math.min(r, w / 2, h);
  return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
}
const f1 = (n) => n.toFixed(1);

function columns({ rows, width, height = 220, label, valueOf, segments, tipOf, ariaLabel }) {
  width = Math.round(width);
  const left = 34, right = 12, top = 22, bottom = 34;
  const plotW = width - left - right, plotH = height - top - bottom;
  const max = Math.max(1, ...rows.map(valueOf));
  const step = plotW / rows.length, barW = Math.max(2, Math.min(44, step * 0.66));
  const ticks = Math.min(max, 4);
  let svg = `<svg class="chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(ariaLabel)}">`;
  for (let i = 0; i <= ticks; i++) {
    const v = Math.round((i / ticks) * max);
    const y = top + plotH - (v / max) * plotH;
    svg += `<line class="chart-grid" x1="${left}" y1="${f1(y)}" x2="${width - right}" y2="${f1(y)}"></line><text x="${left - 8}" y="${f1(y + 4)}" text-anchor="end">${v}</text>`;
  }
  const labelStep = Math.max(1, Math.ceil(rows.length / Math.max(2, Math.floor(plotW / 64))));
  rows.forEach((r, i) => {
    const x = left + i * step + (step - barW) / 2;
    let base = top + plotH;
    const parts = segments(r).filter(([n]) => n > 0);
    parts.forEach(([n, color], j) => {
      const h = (n / max) * plotH - (j > 0 ? 2 : 0); // 2px surface gap between stacked segments
      const y = base - (j > 0 ? 2 : 0) - h;
      const last = j === parts.length - 1;
      svg += last ? `<path d="${topRounded(x, y, barW, h, 4)}" fill="${color}"></path>`
        : `<rect x="${f1(x)}" y="${f1(y)}" width="${f1(barW)}" height="${f1(h)}" fill="${color}"></rect>`;
      base = y;
    });
    const total = valueOf(r);
    if (total && step >= 16) svg += `<text class="chart-value" x="${f1(x + barW / 2)}" y="${f1(Math.max(top + 8, base - 6))}">${total}</text>`;
    // every labelStep-th column, and always the last, minus a regular label too close to it
    const lastI = rows.length - 1;
    if (i === lastI || (i % labelStep === 0 && lastI - i >= labelStep)) svg += `<text class="chart-date" x="${f1(x + barW / 2)}" y="${height - 10}">${esc(label(r))}</text>`;
    // hit target: the whole column, wider than the bar
    svg += `<rect class="hit" x="${f1(left + i * step)}" y="${top}" width="${f1(step)}" height="${plotH}" data-tip="${esc(tipOf(r))}"></rect>`;
  });
  return `${svg}</svg>`;
}

function dayChart(shown, ref, width) {
  const rows = perDay(shown, ref);
  const undated = shown.filter((p) => !p.posted).length;
  const legend = Object.keys(SOURCES).map((k) => `<span class="legend-item"><i style="background:${COLOR[k]}"></i>${SOURCES[k]}</span>`).join("");
  const head = `<div class="chart-head"><h2>Postings by day</h2><div class="legend">${legend}</div></div>`;
  if (!rows.length) return `${head}<div class="chart-empty">No posting dates to chart</div>`;
  const svg = columns({
    rows, width, ariaLabel: "Postings per day, LinkedIn and Indeed stacked",
    label: (r) => fmtDay(r.day), valueOf: (r) => r.linkedin + r.indeed,
    segments: (r) => [[r.linkedin, COLOR.linkedin], [r.indeed, COLOR.indeed]],
    tipOf: (r) => `${fmtFull(r.day)}: ${r.linkedin} LinkedIn, ${r.indeed} Indeed`,
  });
  return `${head}${svg}<p class="dim small">By the date each posting went up${undated ? `; ${undated} without a date aren't shown` : ""}.</p>`;
}

function companyBars(shown) {
  const top = topCompanies(shown, 10);
  const head = "<div class=\"chart-head\"><h2>Companies posting most</h2></div>";
  if (!top.length) return `${head}<div class="chart-empty">No postings match</div>`;
  const max = top[0].count;
  return `${head}<div class="hbars">${top.map((c) => `<button class="hbar" data-company="${esc(c.company)}"
      aria-pressed="${view.q === c.company}" data-tip="${esc(`${c.company}: ${plural(c.count, "posting")}. Click to filter.`)}">
      <span class="hbar-name">${esc(c.company)}</span>
      <span class="hbar-track"><i style="width:${((c.count / max) * 100).toFixed(1)}%"></i></span>
      <span class="hbar-n">${c.count}</span></button>`).join("")}</div>`;
}

function salaryChart(shown, width) {
  const bins = salaryBins(shown);
  const head = "<div class=\"chart-head\"><h2>Advertised pay</h2></div>";
  if (!bins.length) return `${head}<div class="chart-empty">No pay listed in these postings</div>`;
  const listed = bins.reduce((n, b) => n + b.count, 0);
  const svg = columns({
    rows: bins, width, height: 200, ariaLabel: "Postings by advertised annual pay",
    label: (b) => money(b.lo), valueOf: (b) => b.count, segments: (b) => [[b.count, "var(--accent)"]],
    tipOf: (b) => `${plural(b.count, "posting")}: ${money(b.lo)}–${money(b.hi)} a year`,
  });
  return `${head}${svg}<p class="dim small">${listed} of ${shown.length} list pay. Midpoint of each range, per year;
    hourly pay counts as 2,080 hours.</p>`;
}

function table(shown, tracked) {
  if (!shown.length) return `<div class="panel empty-state"><strong>Nothing matches</strong><p>Try a different search or filter.</p></div>`;
  const rows = shown.map((p) => {
    const link = p.url ? `<a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.title)}</a>` : esc(p.title);
    const also = p.also_on.length ? ` <span class="dim">+ ${p.also_on.map((x) => SOURCES[x.split(":")[0]]).join(", ")}</span>` : "";
    const apply = p.url ? `<a class="button-like small" href="#/skills/job-apply?${new URLSearchParams({ links: p.url })}">Apply prompt</a>` : "";
    return `<tr>
      <td class="t-role">${link}${p.easy_apply ? ' <span class="tag">Easy apply</span>' : ""}</td>
      <td>${esc(p.company)}${tracked.has(normCompany(p.company)) ? ' <span class="tag on">In tracker</span>' : ""}</td>
      <td>${p.location ? `${esc(p.location)}${p.workplace ? `<span class="dim"> · ${WORKPLACES[p.workplace]}</span>` : ""}` : esc(p.workplace ? WORKPLACES[p.workplace] : "–")}</td>
      <td class="mono">${p.salary_min ? esc(p.salary_min === p.salary_max ? money(p.salary_min) : `${money(p.salary_min)}–${money(p.salary_max)}`) : '<span class="dim">–</span>'}</td>
      <td class="mono" title="${esc(p.posted_text)}">${p.posted ? `${esc(fmtDay(p.posted))} <span class="dim">${esc(ago(p.posted))}</span>` : esc(p.posted_text || "–")}</td>
      <td><span class="dot" style="--c:${COLOR[p.source]}"></span>${SOURCES[p.source]}${also}</td>
      <td>${apply}</td></tr>`;
  }).join("");
  return `<div class="ledger table-wrap"><table class="postings">
    <thead><tr><th>Role</th><th>Company</th><th>Location</th><th>Pay / yr</th><th>Posted</th><th>Source</th><th></th></tr></thead>
    <tbody>${rows}</tbody></table></div>`;
}

function searchesRun(searches) {
  if (!searches.length) return "";
  const li = searches.map((s) => `<li><span class="dot" style="--c:${COLOR[s.source]}"></span>${SOURCES[s.source]} ·
    ${esc(s.query || "any role")} · ${esc(s.remote ? "remote" : s.location || "anywhere")}${s.days ? ` · last ${plural(s.days, "day")}` : ""}
    · ${s.found == null ? "" : plural(s.found, "result")}${s.note ? ` <span class="warn-text">${esc(s.note)}</span>` : ""}
    <span class="dim">${esc(s.ran_at ? new Date(s.ran_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "")}</span></li>`).join("");
  return `<details class="panel searches"><summary>Searches run (${searches.length})</summary><ul>${li}</ul></details>`;
}
