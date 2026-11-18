// Helpers shared by every page: the API client, formatting, toasts, modals and the top nav.

export const $app = document.getElementById("app");
export const $modalRoot = document.getElementById("modal-root");
const $toastRoot = document.getElementById("toast-root");

// On the static site (GitHub Pages) static-api.js defines window.SWE_STATIC and answers every API
// call in the browser. Nothing can execute Python there, so the controls that need it are disabled.
export const STATIC = Boolean(window.SWE_STATIC);
export const NEEDS_SERVER_NOTE = "Disabled on the static site: running code needs the local server";

export async function api(method, path, body, opts = {}) {
  if (STATIC) return window.SWE_STATIC.handle(method, path, body);
  const res = await fetch(path, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
    keepalive: opts.keepalive || false,
  });
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) {
    const err = new Error((data && data.detail) || `${res.status} ${res.statusText}`);
    err.status = res.status;
    throw err;
  }
  return data;
}

export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

export function fmtClock(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${String(m).padStart(2, "0")}:${sec}`;
}

export function fmtDelta(seconds) {
  if (seconds == null) return "—";
  const sign = seconds > 0 ? "+" : "−";
  return `${sign}${fmtClock(Math.abs(seconds))}`;
}

export function plural(count, word) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

export function fmtDate(epoch) {
  return new Date(epoch * 1000).toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export function storage(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, value);
  } catch { /* storage unavailable: preferences just don't persist */ }
  return null;
}

export function toast(message, kind = "") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = message;
  $toastRoot.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

export function modal({ title, body, actions }) {
  return new Promise((resolve) => {
    const wrap = document.createElement("div");
    wrap.className = "modal-backdrop";
    wrap.innerHTML = `<div class="modal" role="dialog" aria-modal="true">
      <h2>${esc(title)}</h2><div>${body}</div><div class="actions"></div></div>`;
    const bar = wrap.querySelector(".actions");
    for (const action of actions) {
      const btn = document.createElement("button");
      btn.textContent = action.label;
      if (action.kind) btn.className = action.kind;
      btn.onclick = () => { wrap.remove(); resolve(action.value); };
      bar.appendChild(btn);
    }
    wrap.addEventListener("keydown", (e) => {
      if (e.key === "Escape") { wrap.remove(); resolve(null); }
    });
    $modalRoot.appendChild(wrap);
    bar.lastElementChild?.focus();
  });
}

// Strict or pausable: there is no default, you pick by pressing one of the two Start buttons.
export function chooseMode(minutes, firstView, title = `Start a ${minutes}-minute session?`) {
  return modal({
    title,
    body: `<p>The timer starts immediately and you'll see ${firstView}. Choose a timer mode:</p>
      <ul class="mode-help">
        <li><strong>Strict</strong> &mdash; no pausing. Like the real thing: the clock keeps running even if you close the tab.</li>
        <li><strong>Pausable</strong> &mdash; pause any time. While paused, the question and your work are hidden. Every pause is recorded.</li>
      </ul>`,
    actions: [
      { label: "Cancel", value: null, kind: "ghost" },
      { label: "Start strict", value: "strict", kind: "primary" },
      { label: "Start pausable", value: "pausable", kind: "primary" },
    ],
  });
}

// A speed bump, not a gate: reading the answers to something you haven't attempted costs you a
// fresh timed run at it. Cancel is the default so Enter doesn't spoil.
export function confirmSpoil(title, what) {
  return modal({
    title: "This will spoil it",
    body: `<p>You haven't attempted <strong>${esc(title)}</strong> yet. Reading its ${what} now means
      you won't get a fresh, honest timed run at it.</p>`,
    actions: [
      { label: "Show it anyway", value: true },
      { label: "Cancel", value: false, kind: "primary" },
    ],
  });
}

export function topnav(active) {
  const link = (key, href, label) => `<a href="${href}" class="${active === key ? "active" : ""}">${label}</a>`;
  return `<header class="topnav">
    <a class="brand" href="#/"><span class="brand-mark">&lt;/&gt;</span>SWE Practice</a>
    <nav>
      ${link("coding", "#/coding", "Coding")}
      ${link("algo", "#/algo", "Algorithms")}
      ${link("design", "#/design", "System design")}
      ${link("history", "#/history", "History")}
    </nav>
  </header>`;
}

export function levelDots(count, total = 4, overtimeFrom = null) {
  let html = '<span class="level-dots">';
  for (let i = 1; i <= total; i++) {
    const cls = i <= count ? (overtimeFrom && i >= overtimeFrom ? "over" : "on") : "";
    html += `<i class="${cls}"></i>`;
  }
  return `${html}</span>`;
}

// Resizable panes: calls onMove with each pointer move while the gutter is dragged.
export function dragGutter(gutter, onMove) {
  gutter.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    gutter.classList.add("dragging");
    gutter.setPointerCapture(e.pointerId);
    const move = (ev) => onMove(ev);
    const up = () => {
      gutter.classList.remove("dragging");
      gutter.removeEventListener("pointermove", move);
      gutter.removeEventListener("pointerup", up);
    };
    gutter.addEventListener("pointermove", move);
    gutter.addEventListener("pointerup", up);
  });
}

// The left/right split of a session workspace, remembered across sessions.
export function resizableSplit(workspace, gutter) {
  const saved = storage("swe-prac-left-width");
  if (saved) workspace.style.setProperty("--left-width", saved);
  dragGutter(gutter, (e) => {
    const rect = workspace.getBoundingClientRect();
    const pct = Math.min(70, Math.max(20, ((e.clientX - rect.left) / rect.width) * 100));
    workspace.style.setProperty("--left-width", `${pct}%`);
    storage("swe-prac-left-width", `${pct}%`);
  });
}

// ---------------------------------------------------------------- diagrams (mermaid)
// Study pages carry ```mermaid blocks (flowcharts, sequence and state diagrams). Mermaid is 2.5 MB,
// so it loads the first time a page shows one. Data-structure figures are SVG from the server.
let mermaidReady = null;
let diagramSeq = 0;

function loadMermaid() {
  mermaidReady ??= (async () => {
    const res = await fetch(new URL("./vendor/mermaid/mermaid.min.js", import.meta.url));
    if (!res.ok) throw new Error(`could not load the diagram library (${res.status})`);
    // Monaco's AMD loader defines a global `define`. Shadow it (and the CommonJS names) so the
    // libraries bundled inside mermaid don't register with that loader instead of loading.
    // Inside the wrapper the bundle's top-level `var` is local, so read the export from it
    // directly instead of from globalThis.
    // Mermaid 11.4.1 also draws an arrowhead on open links (A --- B, A -.- B, A === B): the
    // flowchart's edge-type mapping has no case for "arrow_open" and falls back to "arrow_point".
    // The second replace maps it to no marker (Mermaid skips an end type it doesn't know).
    const source = (await res.text())
      .replace("globalThis.__esbuild_esm_mermaid.default", "__esbuild_esm_mermaid.default")
      .replace('let e="none",r="arrow_point";switch(t){',
        'let e="none",r=t==="arrow_open"?"none":"arrow_point";switch(t){');
    new Function("define", "module", "exports", "require", source)();
    const css = getComputedStyle(document.documentElement);
    const v = (name) => css.getPropertyValue(name).trim();
    // Series colours (pie slices, chart lines) and section colours (timeline, mindmap).
    const series = [v("--accent"), v("--warn"), v("--pass"), v("--design"), v("--fail"), "#39c5cf", "#db61a2", "#8b949e"];
    const sections = ["#2d4a7a", "#6b4f12", "#1f5a33", "#4a3375", "#6e2a2a", "#1d5a5f", "#5e2a4c", "#3a4154"];
    const scale = {};
    for (let i = 0; i < 12; i++) {
      scale[`cScale${i}`] = sections[i % sections.length];
      scale[`cScalePeer${i}`] = series[i % series.length];
      scale[`cScaleLabel${i}`] = v("--text");
      scale[`pie${i + 1}`] = series[i % series.length];
    }
    // Node colour classes every diagram can use without a classDef: A[Cache]:::good, class B bad
    const tones = {
      accent: ["#1a2740", v("--accent")], good: ["#13301f", v("--pass")], warn: ["#2b2414", v("--warn")],
      bad: ["#3a1618", v("--fail")], purple: ["#251a3d", v("--design")], muted: [v("--bg-elev"), v("--border")],
    };
    const themeCSS = Object.entries(tones).map(([name, [fill, stroke]]) => `
      .node.${name} rect, .node.${name} polygon, .node.${name} circle, .node.${name} ellipse,
      .node.${name} path { fill: ${fill} !important; stroke: ${stroke} !important; }
      .node.${name} .nodeLabel, .node.${name} text { color: ${name === "muted" ? v("--text-dim") : v("--text")} !important; }
      .cluster.${name} rect { fill: ${fill} !important; stroke: ${stroke} !important; }`).join("");
    window.mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: "base",
      darkMode: true,
      themeCSS,
      fontFamily: v("--sans"),
      flowchart: { curve: "basis", padding: 10, nodeSpacing: 40, rankSpacing: 46 },
      sequence: { mirrorActors: false, actorMargin: 60, messageMargin: 34, noteMargin: 10 },
      themeVariables: {
        fontSize: "14px",
        background: v("--bg-input"),
        primaryColor: v("--bg-elev-2"),
        primaryTextColor: v("--text"),
        primaryBorderColor: v("--border-strong"),
        secondaryColor: "#1a2740",
        secondaryTextColor: v("--text"),
        secondaryBorderColor: v("--accent"),
        tertiaryColor: v("--bg-elev"),
        tertiaryTextColor: v("--text"),
        tertiaryBorderColor: v("--border"),
        lineColor: v("--text-dim"),
        textColor: v("--text"),
        mainBkg: v("--bg-elev-2"),
        nodeBorder: v("--border-strong"),
        clusterBkg: "#141823",
        clusterBorder: v("--border"),
        titleColor: v("--text"),
        edgeLabelBackground: v("--bg-input"),
        noteBkgColor: "#2b2414",
        noteTextColor: v("--text"),
        noteBorderColor: v("--warn"),
        actorBkg: v("--bg-elev-2"),
        actorBorder: v("--border-strong"),
        actorTextColor: v("--text"),
        actorLineColor: v("--border-strong"),
        signalColor: v("--text-dim"),
        signalTextColor: v("--text"),
        labelBoxBkgColor: v("--bg-elev-2"),
        labelBoxBorderColor: v("--border-strong"),
        labelTextColor: v("--text"),
        loopTextColor: v("--text-dim"),
        activationBkgColor: v("--bg-elev"),
        activationBorderColor: v("--accent"),
        sequenceNumberColor: v("--bg"),
        attributeBackgroundColorOdd: v("--bg-elev"), // erDiagram attribute rows
        attributeBackgroundColorEven: v("--bg-elev-2"),
        ...scale,
        pieStrokeColor: v("--bg-input"),
        pieOuterStrokeColor: v("--border-strong"),
        pieSectionTextColor: v("--bg"),
        pieTitleTextColor: v("--text"),
        pieLegendTextColor: v("--text"),
        pieOpacity: "0.9",
        xyChart: {
          backgroundColor: v("--bg-input"),
          titleColor: v("--text"),
          xAxisLabelColor: v("--text-dim"),
          xAxisTitleColor: v("--text-dim"),
          xAxisTickColor: v("--border-strong"),
          xAxisLineColor: v("--border-strong"),
          yAxisLabelColor: v("--text-dim"),
          yAxisTitleColor: v("--text-dim"),
          yAxisTickColor: v("--border-strong"),
          yAxisLineColor: v("--border-strong"),
          plotColorPalette: series.join(", "),
        },
      },
    });
    return window.mermaid;
  })();
  return mermaidReady;
}

function diagramError(fig, err) {
  fig.className = "diagram-error";
  fig.innerHTML = `<strong>Diagram error (mermaid):</strong> ${esc(err?.message ?? err)}
    <pre>${esc(fig.dataset.source)}</pre>`;
}

// Replace every ```mermaid block under `root` with its drawing.
export async function renderMermaid(root = document) {
  const blocks = [...root.querySelectorAll("pre > code.language-mermaid")];
  if (!blocks.length) return;
  const figs = blocks.map((code) => {
    const fig = document.createElement("div");
    fig.className = "mermaid-figure pending";
    fig.textContent = "Drawing diagram…";
    fig.dataset.source = code.textContent;
    code.parentElement.replaceWith(fig);
    return fig;
  });
  let mermaid;
  try {
    mermaid = await loadMermaid();
  } catch (err) {
    figs.forEach((fig) => diagramError(fig, err));
    return;
  }
  for (const fig of figs) {
    const id = `mmd-${++diagramSeq}`;
    try {
      const { svg } = await mermaid.render(id, fig.dataset.source);
      fig.innerHTML = svg;
      fig.classList.remove("pending");
    } catch (err) {
      diagramError(fig, err);
    } finally {
      document.getElementById(`d${id}`)?.remove(); // mermaid's scratch element after an error
    }
  }
}

// Syntax-colour the ```python blocks of rendered markdown with Monaco's colorizer (no editor).
const PYTHON_BLOCKS = "pre > code.language-python:not([data-colored])";

async function colorizePython(root = document) {
  const blocks = [...root.querySelectorAll(PYTHON_BLOCKS)];
  if (!blocks.length || !window.monacoReady) return;
  blocks.forEach((code) => { code.dataset.colored = ""; });
  try {
    const monaco = await window.monacoReady;
    monaco.editor.setTheme("vs-dark"); // puts the token colours in the page
    for (const code of blocks) {
      const html = await monaco.editor.colorize(code.textContent.replace(/\n$/, ""), "python", { tabSize: 4 });
      if (code.isConnected) code.innerHTML = html;
    }
  } catch { /* plain text is fine */ }
}

// Draw mermaid blocks and colour Python wherever rendered markdown lands, without every page asking.
export function watchDiagrams() {
  let queued = false;
  new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      if (document.querySelector("pre > code.language-mermaid")) renderMermaid(document);
      if (document.querySelector(PYTHON_BLOCKS)) colorizePython(document);
    });
  }).observe(document.body, { childList: true, subtree: true });
}
