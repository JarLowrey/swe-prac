// SWE Practice frontend: hash-routed single page (home, session, review, history).

const $app = document.getElementById("app");
const $modalRoot = document.getElementById("modal-root");
const $toastRoot = document.getElementById("toast-root");

// ---------------------------------------------------------------- utilities
async function api(method, path, body, opts = {}) {
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

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function fmtClock(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${String(m).padStart(2, "0")}:${sec}`;
}

function fmtMinutes(seconds) {
  if (seconds == null) return "—";
  return `${(seconds / 60).toFixed(1)} min`;
}

function fmtDelta(seconds) {
  if (seconds == null) return "—";
  const sign = seconds > 0 ? "+" : "−";
  return `${sign}${fmtClock(Math.abs(seconds))}`;
}

function plural(count, word) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

function fmtDate(epoch) {
  return new Date(epoch * 1000).toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function storage(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, value);
  } catch { /* storage unavailable: preferences just don't persist */ }
  return null;
}

function toast(message, kind = "") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = message;
  $toastRoot.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

function modal({ title, body, actions }) {
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

function topnav(active) {
  return `<header class="topnav">
    <a class="brand" href="#/"><span class="brand-mark">&lt;/&gt;</span>SWE Practice</a>
    <nav>
      <a href="#/" class="${active === "home" ? "active" : ""}">Practice</a>
      <a href="#/history" class="${active === "history" ? "active" : ""}">History</a>
    </nav>
  </header>`;
}

function levelDots(count, total = 4, overtimeFrom = null) {
  let html = '<span class="level-dots">';
  for (let i = 1; i <= total; i++) {
    const cls = i <= count ? (overtimeFrom && i >= overtimeFrom ? "over" : "on") : "";
    html += `<i class="${cls}"></i>`;
  }
  return `${html}</span>`;
}

// ---------------------------------------------------------------- router
let cleanup = null;

async function route() {
  if (cleanup) { await cleanup(); cleanup = null; }
  $modalRoot.innerHTML = "";
  const hash = location.hash || "#/";
  const m = hash.match(/^#\/(session|review)\/(\d+)$/);
  try {
    if (m && m[1] === "session") await renderSession(Number(m[2]));
    else if (m && m[1] === "review") await renderReview(Number(m[2]));
    else if (hash === "#/history") await renderHistory();
    else await renderHome();
  } catch (err) {
    $app.innerHTML = `${topnav("")}<div class="page"><div class="callout bad">${esc(err.message)}</div>
      <a href="#/">Back to problems</a></div>`;
  }
}
window.addEventListener("hashchange", route);

// ---------------------------------------------------------------- home
async function renderHome() {
  const [{ problems }, { session: active }] = await Promise.all([
    api("GET", "/api/problems"), api("GET", "/api/active"),
  ]);
  let mode = storage("swe-prac-mode") || "strict";
  const preferUnseen = storage("swe-prac-prefer-unseen") !== "0";

  const banner = active ? `<div class="banner">
      <div><strong>Session in progress:</strong> ${esc(active.problem.title)} ·
        ${active.mode} · Level ${Math.min(active.current_level, 4)} ·
        <span class="mono">${active.timer.paused ? "paused" : active.timer.overtime ? "overtime" : fmtClock(active.timer.remaining) + " left"}</span></div>
      <div style="display:flex;gap:8px"><button class="primary" data-resume>Resume</button>
        <button class="danger" data-end-active>End session</button></div>
    </div>` : "";

  const cards = problems.map((p) => `<article class="problem-card">
      <span class="num">PROBLEM ${p.number}</span>
      <h3>${esc(p.title)}</h3>
      <p>${esc(p.summary)}</p>
      <div class="meta">
        <span class="dim" style="font-size:12px">${p.attempts ? `${p.attempts} attempt${p.attempts > 1 ? "s" : ""} · best ${levelDots(p.best_timed_levels || 0)}` : "Not attempted"}</span>
        <button class="primary small" data-start="${esc(p.id)}" ${active ? "disabled" : ""}>Start</button>
      </div>
    </article>`).join("");

  $app.innerHTML = `${topnav("home")}<main class="page">
    <h1>90-minute coding assessment practice</h1>
    <p class="lead">One problem, four levels, revealed one at a time. Each level unlocks when every shown and hidden test up to it passes.</p>
    ${banner}
    <h2 class="section-title">Timer mode</h2>
    <div class="mode-picker">
      <label class="mode-option" data-mode="strict"><input type="radio" name="mode" value="strict">
        <div><strong>Strict</strong><span class="dim">90 minutes, no pausing. Like the real thing: the clock keeps running even if you close the tab.</span></div></label>
      <label class="mode-option" data-mode="pausable"><input type="radio" name="mode" value="pausable">
        <div><strong>Pausable</strong><span class="dim">Pause any time. While paused, the problem and your code are hidden. Every pause is recorded.</span></div></label>
    </div>
    <h2 class="section-title">Problems</h2>
    <div class="random-row">
      <button data-random ${active ? "disabled" : ""}>🎲 Start a random problem</button>
      <label><input type="checkbox" data-unseen ${preferUnseen ? "checked" : ""}> Prefer problems I haven't tried</label>
    </div>
    <div class="problem-grid">${cards || '<p class="dim">No problems are built yet. Run <code>tools/build_problem.py --all</code>.</p>'}</div>
  </main>`;

  const syncMode = () => {
    $app.querySelectorAll(".mode-option").forEach((el) => {
      const on = el.dataset.mode === mode;
      el.classList.toggle("selected", on);
      el.querySelector("input").checked = on;
    });
  };
  $app.querySelectorAll(".mode-option").forEach((el) => {
    el.addEventListener("click", () => { mode = el.dataset.mode; storage("swe-prac-mode", mode); syncMode(); });
  });
  syncMode();

  const unseenBox = $app.querySelector("[data-unseen]");
  unseenBox.addEventListener("change", () => storage("swe-prac-prefer-unseen", unseenBox.checked ? "1" : "0"));

  const start = async (problemId) => {
    const label = mode === "strict" ? "Strict (no pausing)" : "Pausable";
    const choice = await modal({
      title: "Start a 90-minute session?",
      body: `<p>Mode: <strong>${label}</strong>. The timer starts immediately and you'll see Level 1 only.</p>`,
      actions: [{ label: "Cancel", value: false, kind: "ghost" }, { label: "Start", value: true, kind: "primary" }],
    });
    if (!choice) return;
    try {
      const s = await api("POST", "/api/sessions", {
        problem_id: problemId, mode, prefer_unseen: unseenBox.checked,
      });
      location.hash = `#/session/${s.id}`;
    } catch (err) { toast(err.message, "bad"); }
  };
  $app.querySelectorAll("[data-start]").forEach((b) => b.addEventListener("click", () => start(b.dataset.start)));
  $app.querySelector("[data-random]").addEventListener("click", () => start(null));
  $app.querySelector("[data-resume]")?.addEventListener("click", () => { location.hash = `#/session/${active.id}`; });
  $app.querySelector("[data-end-active]")?.addEventListener("click", async () => {
    if (await confirmEnd()) {
      await api("POST", `/api/sessions/${active.id}/end`);
      location.hash = `#/review/${active.id}`;
    }
  });
}

function confirmEnd() {
  return modal({
    title: "End this session?",
    body: "<p>The session will be scored and locked. Hints, the solution analysis and the reference solution unlock on the review page.</p>",
    actions: [{ label: "Keep working", value: false, kind: "ghost" }, { label: "End & review", value: true, kind: "primary" }],
  });
}

// ---------------------------------------------------------------- session
async function renderSession(sessionId) {
  let session;
  try {
    session = await api("GET", `/api/sessions/${sessionId}`);
  } catch (err) {
    if (err.status === 410) { location.hash = `#/review/${sessionId}`; return; }
    throw err;
  }
  const monaco = await window.monacoReady;

  const st = {
    session,
    timer: { ...session.timer, syncedAt: performance.now() },
    selectedLevel: Math.min(session.current_level, 4),
    file: "solution",
    resultsTab: "tests",
    busy: false,
    dirty: false,
    lastSaved: null,
    lastResult: null,
    lint: { issues: [], error: null },
    scratchOut: null,
    timeUpShown: storage(`swe-prac-timeup-${sessionId}`) === "1",
  };

  $app.innerHTML = `<div class="session">
    <div class="session-bar">
      <a href="#/" class="ghost" title="Back to problems" style="color:var(--text-dim)">←</a>
      <span class="title">${esc(session.problem.title)}</span>
      <span class="level-pills" data-pills></span>
      <span class="mode-badge">${session.mode}</span>
      <span class="spacer"></span>
      <span class="timer" data-timer>--:--</span>
      <button data-pause class="${session.mode === "pausable" ? "" : "hidden"}">Pause</button>
      <button data-end class="danger">End session</button>
    </div>
    <div class="workspace" data-workspace>
      <section class="statement-pane" data-blur>
        <div class="tabs" data-level-tabs></div>
        <div class="scroll" data-statement></div>
      </section>
      <div class="gutter" data-gutter-x></div>
      <section class="code-pane" data-blur>
        <div class="editor-toolbar">
          <div class="file-tabs">
            <button class="file-tab active" data-file="solution">solution.py</button>
            <button class="file-tab" data-file="scratch">scratch.py</button>
            <button class="file-tab" data-file="tests" title="The shown tests for your unlocked levels, as code. Run executes exactly these; Submit also runs the hidden tests.">tests.py <span class="ro">read-only</span></button>
          </div>
          <span class="save-state" data-save-state></span>
          <button data-format title="Format with ruff (Shift+Alt+F)">Format</button>
          <button data-scratch title="Run scratch.py">Run scratch</button>
          <button data-run title="Run shown tests (Ctrl+Enter)">▶ Run <kbd>Ctrl+↵</kbd></button>
          <button data-submit class="primary" title="Run shown + hidden tests (Ctrl+Shift+Enter)">Submit <kbd style="color:#dfe8ff;border-color:#9bb8ff">Ctrl+⇧+↵</kbd></button>
        </div>
        <div class="editor-host" data-editor-host></div>
        <div class="gutter horizontal" data-gutter-y></div>
        <div class="results-pane">
          <div class="tabs" data-result-tabs></div>
          <div class="scroll"><div class="results-body" data-results></div></div>
        </div>
      </section>
    </div>
  </div>`;

  const q = (sel) => $app.querySelector(sel);
  const workspace = q("[data-workspace]");

  // ----- editors
  const solutionModel = monaco.editor.createModel(session.code, "python");
  const scratchModel = monaco.editor.createModel(session.scratch, "python");
  const testsModel = monaco.editor.createModel(session.tests_source, "python");
  const editor = monaco.editor.create(q("[data-editor-host]"), {
    model: solutionModel,
    theme: "vs-dark",
    fontSize: 14,
    fontFamily: "'Cascadia Code', 'JetBrains Mono', Consolas, monospace",
    minimap: { enabled: false },
    automaticLayout: true,
    tabSize: 4,
    insertSpaces: true,
    rulers: [100],
    scrollBeyondLastLine: false,
    renderWhitespace: "selection",
    padding: { top: 8 },
    fixedOverflowWidgets: true,
  });

  const formatProvider = monaco.languages.registerDocumentFormattingEditProvider("python", {
    async provideDocumentFormattingEdits(model) {
      try {
        const res = await api("POST", "/api/format", { code: model.getValue() });
        if (res.error) { toast("Format failed: fix syntax errors first", "bad"); return []; }
        return [{ range: model.getFullModelRange(), text: res.code }];
      } catch (err) { toast(err.message, "bad"); return []; }
    },
  });

  const markDirty = () => { st.dirty = true; renderSaveState(); scheduleLint(); };
  const subs = [solutionModel.onDidChangeContent(markDirty), scratchModel.onDidChangeContent(markDirty)];

  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => doRun("run"));
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Enter, () => doRun("submit"));
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => save());

  // ----- saving
  function renderSaveState() {
    const el = q("[data-save-state]");
    if (!el) return;
    el.textContent = st.dirty ? "Unsaved…" : st.lastSaved ? "Saved" : "";
  }

  async function save({ keepalive = false } = {}) {
    if (!st.dirty || st.timer.paused) return;
    const body = { code: solutionModel.getValue(), scratch: scratchModel.getValue() };
    st.dirty = false;
    try {
      const res = await api("PUT", `/api/sessions/${sessionId}/code`, body, { keepalive });
      st.lastSaved = Date.now();
      if (res?.timer) syncTimer(res.timer);
    } catch (err) {
      st.dirty = true;
      if (err.status !== 409) toast(`Autosave failed: ${err.message}`, "bad");
    }
    renderSaveState();
  }
  const autosave = setInterval(save, 3000);
  const beforeUnload = () => { save({ keepalive: true }); };
  window.addEventListener("beforeunload", beforeUnload);

  // ----- lint (idle + every run/submit)
  let lintTimer = null;
  function scheduleLint() {
    clearTimeout(lintTimer);
    lintTimer = setTimeout(runLint, 1500);
  }
  async function runLint() {
    if (st.timer.paused) return;
    try {
      setLint(await api("POST", `/api/sessions/${sessionId}/lint`, { code: solutionModel.getValue() }));
    } catch { /* lint is best-effort */ }
  }
  function setLint(lint) {
    st.lint = lint;
    monaco.editor.setModelMarkers(solutionModel, "ruff", lint.issues.map((i) => ({
      startLineNumber: i.row, startColumn: i.col, endLineNumber: i.end_row,
      endColumn: Math.max(i.end_col, i.col + 1),
      message: `${i.message} (${i.code})`,
      severity: i.code === "syntax" || i.code.startsWith("F") || i.code.startsWith("E9")
        ? monaco.MarkerSeverity.Error : monaco.MarkerSeverity.Warning,
      source: "ruff",
    })));
    renderResultTabs();
    if (st.resultsTab === "lint") renderResults();
  }

  // ----- timer
  function syncTimer(t) { st.timer = { ...t, syncedAt: performance.now() }; renderTimer(); }
  function currentElapsed() {
    const t = st.timer;
    if (t.paused || t.status !== "active") return t.elapsed;
    return t.elapsed + (performance.now() - t.syncedAt) / 1000;
  }
  function renderTimer() {
    const el = q("[data-timer]");
    if (!el) return;
    const elapsed = currentElapsed();
    const remaining = st.timer.limit - elapsed;
    el.className = "timer";
    if (st.timer.paused) {
      el.classList.add("paused");
      el.textContent = `⏸ ${fmtClock(remaining)}`;
    } else if (remaining <= 0) {
      el.classList.add("overtime");
      el.textContent = `+${fmtClock(-remaining)} over`;
      if (!st.timeUpShown) { st.timeUpShown = true; storage(`swe-prac-timeup-${sessionId}`, "1"); showTimeUp(); }
    } else {
      if (remaining <= 300) el.classList.add("critical");
      else if (remaining <= 900) el.classList.add("low");
      el.textContent = fmtClock(remaining);
    }
    el.title = `Elapsed ${fmtClock(elapsed)} of ${fmtClock(st.timer.limit)}`;
    const pauseBtn = q("[data-pause]");
    if (pauseBtn) {
      pauseBtn.textContent = st.timer.paused ? "Resume" : "Pause";
      pauseBtn.disabled = !st.timer.paused && remaining <= 0;
    }
  }
  const tick = setInterval(renderTimer, 250);
  const resync = setInterval(async () => {
    try { syncTimer(await api("GET", `/api/sessions/${sessionId}/timer`)); } catch { /* offline */ }
  }, 15000);

  async function showTimeUp() {
    const done = st.session.levels.filter((l) => l.completed_at != null).length;
    const choice = await modal({
      title: "⏰ Time's up",
      body: `<p>Timed result: <strong>${done} of 4 levels</strong>. That score is locked in.</p>
        <p>You can keep going untimed; anything you finish from now on is recorded as overtime.</p>`,
      actions: [{ label: "Keep going (overtime)", value: "keep", kind: "ghost" }, { label: "End & review", value: "end", kind: "primary" }],
    });
    if (choice === "end") await endSession(false);
  }

  // ----- pause overlay
  function applyPaused() {
    const paused = st.timer.paused;
    $app.querySelectorAll("[data-blur]").forEach((el) => el.classList.toggle("blurred", paused));
    syncReadOnly();
    let overlay = q("[data-overlay]");
    if (paused && !overlay) {
      overlay = document.createElement("div");
      overlay.className = "overlay";
      overlay.dataset.overlay = "";
      overlay.innerHTML = `<div class="card"><h2>Paused</h2>
        <p>The problem and your code are hidden while the clock is stopped. This pause is recorded.</p>
        <button class="primary" data-resume>Resume</button></div>`;
      overlay.querySelector("[data-resume]").onclick = togglePause;
      workspace.appendChild(overlay);
    } else if (!paused && overlay) {
      overlay.remove();
    }
    q("[data-run]").disabled = q("[data-submit]").disabled = q("[data-scratch]").disabled = paused || st.busy;
  }

  async function togglePause() {
    try {
      if (!st.timer.paused) await save();
      const t = await api("POST", `/api/sessions/${sessionId}/${st.timer.paused ? "resume" : "pause"}`);
      syncTimer(t);
      applyPaused();
    } catch (err) { toast(err.message, "bad"); }
  }

  // ----- statement
  function renderLevelPills() {
    const pills = [1, 2, 3, 4].map((lv) => {
      const info = st.session.levels.find((l) => l.level === lv);
      const cls = info?.completed_at != null ? "done" : lv === st.session.current_level ? "current" : "";
      const label = info?.completed_at != null ? `L${lv} ✓` : lv > st.session.current_level ? `L${lv} 🔒` : `L${lv}`;
      return `<span class="level-pill ${cls}" title="${info ? esc(info.title) : "Locked"}">${label}</span>`;
    });
    q("[data-pills]").innerHTML = pills.join("");
  }

  function renderStatement() {
    const tabs = st.session.levels.map((l) => {
      const done = l.completed_at != null;
      return `<button class="tab ${l.level === st.selectedLevel ? "active" : ""}" data-level="${l.level}">
        Level ${l.level}${done ? ' <span class="badge good">✓</span>' : ""}</button>`;
    });
    const locked = [];
    for (let lv = st.session.levels.length + 1; lv <= 4; lv++) {
      locked.push(`<button class="tab" disabled title="Pass all tests to unlock">Level ${lv} 🔒</button>`);
    }
    q("[data-level-tabs]").innerHTML = tabs.join("") + locked.join("");
    q("[data-level-tabs]").querySelectorAll("[data-level]").forEach((b) => {
      b.onclick = () => { st.selectedLevel = Number(b.dataset.level); renderStatement(); };
    });
    const info = st.session.levels.find((l) => l.level === st.selectedLevel);
    const target = st.session.pacing[info.level];
    const doneNote = info.completed_at != null
      ? `<div class="passed-note">✓ Passed at ${fmtClock(info.completed_at)} (target ${fmtClock(target)})</div>` : "";
    const allDone = st.session.all_levels_done
      ? `<div class="callout good" style="margin:12px 22px 0"><strong>All four levels complete.</strong>
          <span class="dim">End the session to see your results, hints and the reference solution.</span></div>` : "";
    q("[data-statement]").innerHTML = `${allDone}
      <details class="conventions"><summary>Conventions (apply to every level)</summary>
        <div class="md">${st.session.conventions_html}</div></details>
      <div class="statement">
        <h2>Level ${info.level}: ${esc(info.title)}</h2>
        <div class="level-meta">Pacing target: done by ${fmtClock(target)} · Class <code>${esc(st.session.problem.class_name)}</code></div>
        ${info.statement_html}
        ${doneNote}
        <div class="stub-box">
          <header><span>Level ${info.level} method stubs</span>
            <span><button class="small" data-copy-stubs>Copy</button>
            <button class="small" data-insert-stubs title="Insert at the cursor in solution.py">Insert at cursor</button></span></header>
          <pre>${esc(info.stubs)}</pre>
        </div>
      </div>`;
    q("[data-copy-stubs]").onclick = async () => {
      try { await navigator.clipboard.writeText(info.stubs); toast("Stubs copied"); } catch { toast("Clipboard unavailable", "bad"); }
    };
    q("[data-insert-stubs]").onclick = () => insertStubs(info.stubs);
  }

  function insertStubs(text) {
    if (st.timer.paused) return;
    switchFile("solution");
    const pos = editor.getPosition() || { lineNumber: solutionModel.getLineCount(), column: 1 };
    const range = new monaco.Range(pos.lineNumber, 1, pos.lineNumber, 1);
    editor.executeEdits("stubs", [{ range, text: `${text}\n`, forceMoveMarkers: true }]);
    editor.focus();
  }

  // ----- files
  const models = { solution: solutionModel, scratch: scratchModel, tests: testsModel };
  // tests.py is never editable; the other files lock while the session is paused.
  function syncReadOnly() {
    editor.updateOptions({ readOnly: st.timer.paused || st.file === "tests" });
    q("[data-format]").disabled = st.file === "tests";
  }
  function switchFile(name) {
    st.file = name;
    editor.setModel(models[name]);
    syncReadOnly();
    $app.querySelectorAll("[data-file]").forEach((b) => b.classList.toggle("active", b.dataset.file === name));
  }
  $app.querySelectorAll("[data-file]").forEach((b) => { b.onclick = () => switchFile(b.dataset.file); });

  // ----- results
  function renderResultTabs() {
    const r = st.lastResult;
    let testBadge = "";
    if (r) {
      const counts = totals(r);
      const good = r.all_passed;
      testBadge = `<span class="badge ${good ? "good" : "bad"}">${counts.passed}/${counts.total}</span>`;
    }
    const lintCount = st.lint.issues.length;
    const lintBadge = `<span class="badge ${lintCount ? "warnb" : ""}">${lintCount}</span>`;
    const tabs = [
      ["tests", `Tests ${testBadge}`],
      ["lint", `Lint ${lintBadge}`],
      ["scratch", "Scratch output"],
    ];
    q("[data-result-tabs]").innerHTML = tabs.map(([key, label]) =>
      `<button class="tab ${st.resultsTab === key ? "active" : ""}" data-rtab="${key}">${label}</button>`).join("");
    q("[data-result-tabs]").querySelectorAll("[data-rtab]").forEach((b) => {
      b.onclick = () => { st.resultsTab = b.dataset.rtab; renderResultTabs(); renderResults(); };
    });
  }

  function totals(r) {
    let passed = 0, total = 0;
    for (const c of Object.values(r.breakdown)) {
      passed += c.shown_passed + (r.kind === "submit" ? c.hidden_passed : 0);
      total += c.shown_total + (r.kind === "submit" ? c.hidden_total : 0);
    }
    return { passed, total };
  }

  function renderResults() {
    const el = q("[data-results]");
    if (st.resultsTab === "lint") { el.innerHTML = renderLint(); bindLint(el); return; }
    if (st.resultsTab === "scratch") { el.innerHTML = renderScratch(); return; }
    if (st.busy) { el.innerHTML = '<div class="empty">Running…</div>'; return; }
    const r = st.lastResult;
    if (!r) {
      el.innerHTML = `<div class="empty">The shown tests are in <code>tests.py</code>. <kbd>Ctrl+↵</kbd> Run checks them with full details.
        <kbd>Ctrl+⇧+↵</kbd> Submit also runs the hidden tests (counts only) and unlocks the next level when everything passes.</div>`;
      return;
    }
    el.innerHTML = renderTestResult(r);
  }

  function renderTestResult(r) {
    const { passed, total } = totals(r);
    const parts = [];
    const kindLabel = r.kind === "submit" ? "Submit (shown + hidden)" : "Run (shown tests)";
    parts.push(`<div class="summary-row">
      <strong>${kindLabel}</strong>
      <span class="chip ${r.all_passed ? "good" : "bad"}">${passed}/${total} passed</span>
      <span class="faint">Levels 1–${r.level} · ${r.ms} ms</span></div>`);
    if (r.unlocked) {
      const msg = r.unlocked.new_level > 4 ? "All four levels complete!" : `Level ${r.unlocked.new_level} unlocked.`;
      parts.push(`<div class="callout good"><strong>Level ${r.unlocked.completed} passed.</strong> ${msg}</div>`);
    } else if (r.kind === "run" && r.all_passed) {
      parts.push(`<div class="callout info">All shown tests pass. <strong>Submit</strong> to run the hidden tests and unlock the next level.</div>`);
    }
    if (r.import_error) {
      parts.push(`<div class="callout bad"><strong>Your code failed to load</strong><pre>${esc(r.import_error)}</pre>
        ${r.import_stdout ? `<div class="block-label">Output</div><pre>${esc(r.import_stdout)}</pre>` : ""}</div>`);
    }
    if (r.crashed) parts.push(`<div class="callout bad"><strong>Test process crashed</strong><pre>${esc(r.crashed)}</pre></div>`);
    if (r.timed_out) parts.push(`<div class="callout bad"><strong>Timed out.</strong> The run was stopped after the time limit; tests that didn't finish count as failed.</div>`);

    const rows = Object.entries(r.breakdown).sort().map(([lv, c]) => {
      const hidden = r.kind === "submit"
        ? `<td class="${c.hidden_passed === c.hidden_total ? "pass" : "fail"}">${c.hidden_passed}/${c.hidden_total}</td>`
        : '<td class="faint">submit to run</td>';
      return `<tr><td>Level ${lv}</td><td class="${c.shown_passed === c.shown_total ? "pass" : "fail"}">${c.shown_passed}/${c.shown_total}</td>${hidden}</tr>`;
    });
    parts.push(`<table class="level-results"><tr><th>Level</th><th>Shown</th><th>Hidden</th></tr>${rows.join("")}</table>`);

    for (const t of r.shown) {
      const open = !t.passed ? "open" : "";
      const steps = t.steps.map((s, i) => {
        const bad = s.ok === false;
        const mark = bad ? '<span class="fail">✗</span>' : s.checked ? '<span class="pass">✓</span>' : '<span class="faint">·</span>';
        return `<tr class="${bad ? "bad" : ""}"><td class="mark">${mark}</td><td class="faint">${i + 1}</td>
          <td class="call">${esc(s.call)}(${esc(s.args)})</td>
          <td>${s.checked ? esc(s.expect) : '<span class="faint">(not checked)</span>'}</td>
          <td>${esc(s.actual)}</td></tr>`;
      }).join("");
      const notRun = t.total_steps - t.steps.length;
      parts.push(`<details class="test" ${open}>
        <summary>${t.passed ? '<span class="pass">✓</span>' : '<span class="fail">✗</span>'}
          <span class="test-name">${esc(t.name)}</span>
          <span class="faint mono" style="font-size:12px">L${t.level} · ${t.total_steps} steps</span></summary>
        <div class="body">
          ${t.error ? `<div class="callout bad"><pre>${esc(t.error)}</pre></div>` : ""}
          ${t.steps.length ? `<table class="steps"><tr><th></th><th>#</th><th>Call</th><th>Expected</th><th>Got</th></tr>${steps}</table>` : ""}
          ${notRun > 0 && t.ran ? `<div class="faint" style="margin-top:6px">${notRun} more step${notRun > 1 ? "s" : ""} not run (a test stops at its first failure).</div>` : ""}
          ${!t.ran ? '<div class="faint">Not run.</div>' : ""}
          ${t.stdout ? `<div class="block-label">stdout</div><pre class="out">${esc(t.stdout)}</pre>` : ""}
        </div></details>`);
    }
    if (r.kind === "submit") {
      parts.push('<p class="faint" style="font-size:12px">Hidden tests report pass counts only, never their inputs or expected values.</p>');
    }
    return parts.join("");
  }

  function renderLint() {
    const { issues, error } = st.lint;
    if (error) return `<div class="callout bad"><pre>${esc(error)}</pre></div>`;
    if (!issues.length) return '<div class="empty">✓ No lint issues (ruff).</div>';
    return `<p class="faint" style="margin-top:0;font-size:12px">ruff · informational only, never blocks a level. Click an issue to jump to it.</p>
      <ul class="lint-list">${issues.map((i, n) => `<li data-issue="${n}">
        <span class="pos">${i.row}:${i.col}</span><span class="code">${esc(i.code)}</span>
        <span>${esc(i.message)}${i.fixable ? ' <span class="faint">(auto-fixable)</span>' : ""}</span></li>`).join("")}</ul>`;
  }
  function bindLint(el) {
    el.querySelectorAll("[data-issue]").forEach((li) => {
      li.onclick = () => {
        const i = st.lint.issues[Number(li.dataset.issue)];
        switchFile("solution");
        editor.revealLineInCenter(i.row);
        editor.setPosition({ lineNumber: i.row, column: i.col });
        editor.focus();
      };
    });
  }

  function renderScratch() {
    const o = st.scratchOut;
    if (!o) return `<div class="empty">Write experiments in <code>scratch.py</code> (it starts with <code>from solution import *</code>) and press <strong>Run scratch</strong>.</div>`;
    return `<div class="summary-row"><strong>scratch.py</strong>
        <span class="chip ${o.exit_code === 0 ? "good" : "bad"}">${o.timed_out ? "timed out" : `exit ${o.exit_code}`}</span>
        <span class="faint">${o.ms} ms</span></div>
      <div class="block-label">stdout</div><pre class="out">${esc(o.stdout) || '<span class="faint">(empty)</span>'}</pre>
      ${o.stderr ? `<div class="block-label">stderr</div><pre class="out fail">${esc(o.stderr)}</pre>` : ""}`;
  }

  // ----- actions
  function setBusy(busy) {
    st.busy = busy;
    q("[data-run]").disabled = q("[data-submit]").disabled = q("[data-scratch]").disabled = busy || st.timer.paused;
  }

  async function doRun(kind) {
    if (st.busy || st.timer.paused) return;
    setBusy(true);
    st.resultsTab = "tests";
    renderResultTabs();
    renderResults();
    try {
      const r = await api("POST", `/api/sessions/${sessionId}/${kind}`, {
        code: solutionModel.getValue(), scratch: scratchModel.getValue(),
      });
      st.dirty = false;
      st.lastSaved = Date.now();
      st.lastResult = r;
      setLint(r.lint);
      if (r.unlocked && r.session) {
        st.session = r.session;
        testsModel.setValue(r.session.tests_source);  // the new level's shown tests
        syncTimer(r.session.timer);
        st.selectedLevel = Math.min(r.session.current_level, 4);
        renderLevelPills();
        renderStatement();
        if (r.unlocked.new_level <= 4) {
          toast(`Level ${r.unlocked.completed} passed: Level ${r.unlocked.new_level} unlocked`, "good");
        } else {
          toast("All four levels complete!", "good");
        }
      }
    } catch (err) {
      toast(err.message, "bad");
    } finally {
      setBusy(false);
      renderSaveState();
      renderResultTabs();
      renderResults();
    }
  }

  async function doScratch() {
    if (st.busy || st.timer.paused) return;
    setBusy(true);
    try {
      st.scratchOut = await api("POST", `/api/sessions/${sessionId}/scratch`, {
        code: solutionModel.getValue(), scratch: scratchModel.getValue(),
      });
      st.dirty = false;
      st.lastSaved = Date.now();
    } catch (err) { toast(err.message, "bad"); }
    setBusy(false);
    st.resultsTab = "scratch";
    renderSaveState();
    renderResultTabs();
    renderResults();
  }

  async function endSession(ask = true) {
    if (ask && !(await confirmEnd())) return;
    try {
      const body = st.timer.paused ? undefined : { code: solutionModel.getValue(), scratch: scratchModel.getValue() };
      await api("POST", `/api/sessions/${sessionId}/end`, body);
      st.dirty = false;
      location.hash = `#/review/${sessionId}`;
    } catch (err) { toast(err.message, "bad"); }
  }

  q("[data-run]").onclick = () => doRun("run");
  q("[data-submit]").onclick = () => doRun("submit");
  q("[data-scratch]").onclick = doScratch;
  q("[data-format]").onclick = () => editor.getAction("editor.action.formatDocument").run();
  q("[data-pause]").onclick = togglePause;
  q("[data-end]").onclick = () => endSession(true);

  const keyHandler = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !editor.hasTextFocus()) {
      e.preventDefault();
      doRun(e.shiftKey ? "submit" : "run");
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); }
  };
  window.addEventListener("keydown", keyHandler);

  // ----- resizable panes
  function dragGutter(gutter, onMove) {
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
  const savedLeft = storage("swe-prac-left-width");
  const savedBottom = storage("swe-prac-bottom-height");
  if (savedLeft) workspace.style.setProperty("--left-width", savedLeft);
  if (savedBottom) q(".code-pane").style.setProperty("--bottom-height", savedBottom);
  dragGutter(q("[data-gutter-x]"), (e) => {
    const rect = workspace.getBoundingClientRect();
    const pct = Math.min(70, Math.max(20, ((e.clientX - rect.left) / rect.width) * 100));
    workspace.style.setProperty("--left-width", `${pct}%`);
    storage("swe-prac-left-width", `${pct}%`);
  });
  dragGutter(q("[data-gutter-y]"), (e) => {
    const pane = q(".code-pane").getBoundingClientRect();
    const px = Math.min(pane.height - 120, Math.max(80, pane.bottom - e.clientY));
    q(".code-pane").style.setProperty("--bottom-height", `${px}px`);
    storage("swe-prac-bottom-height", `${px}px`);
  });

  // ----- initial paint
  renderLevelPills();
  renderStatement();
  renderResultTabs();
  renderResults();
  renderTimer();
  applyPaused();
  runLint();
  if (!st.timer.paused) editor.focus();

  cleanup = async () => {
    await save({ keepalive: true });
    clearInterval(autosave); clearInterval(tick); clearInterval(resync); clearTimeout(lintTimer);
    window.removeEventListener("beforeunload", beforeUnload);
    window.removeEventListener("keydown", keyHandler);
    subs.forEach((s) => s.dispose());
    formatProvider.dispose();
    editor.dispose();
    solutionModel.dispose();
    scratchModel.dispose();
    testsModel.dispose();
  };
}

// ---------------------------------------------------------------- review
async function renderReview(sessionId) {
  let data;
  try {
    data = await api("GET", `/api/sessions/${sessionId}/review`);
  } catch (err) {
    if (err.status === 409) { location.hash = `#/session/${sessionId}`; return; }
    throw err;
  }
  const r = data.results;
  const ratio = (x) => x ? `${x.passed}/${x.total} tests` : "no submit";
  const stopNote = (part) => part.stopped_level
    ? `Stopped on Level ${part.stopped_level} · ${ratio(part.stopped_level_ratio)}` : "All levels complete";
  const pacingRows = r.levels.map((lv) => {
    const status = lv.completed_at == null ? '<span class="faint">not completed</span>'
      : lv.overtime ? '<span class="warn">overtime</span>'
      : lv.delta <= 0 ? '<span class="pass">ahead</span>' : '<span class="warn">behind</span>';
    return `<tr><td>Level ${lv.level}: ${esc(data.levels[lv.level - 1].title)}</td>
      <td>${fmtClock(lv.target)}</td>
      <td>${lv.completed_at == null ? "—" : fmtClock(lv.completed_at)}</td>
      <td>${lv.split == null ? "—" : fmtClock(lv.split)}</td>
      <td>${fmtDelta(lv.delta)}</td><td>${status}</td></tr>`;
  }).join("");
  const firstOver = r.levels.find((l) => l.overtime)?.level ?? null;

  $app.innerHTML = `${topnav("")}<main class="page">
    <p class="faint" style="margin:0 0 4px"><a href="#/history">← History</a></p>
    <h1>${esc(data.problem.title)}</h1>
    <p class="lead">${data.mode === "strict" ? "Strict" : "Pausable"} session · ${fmtDate(data.started_at)}</p>
    <div class="stat-grid">
      <div class="stat"><div class="label">Timed result</div>
        <div class="value">${r.timed.levels_completed}/4 ${levelDots(r.timed.levels_completed)}</div>
        <div class="sub">${stopNote(r.timed)}</div></div>
      <div class="stat"><div class="label">Including overtime</div>
        <div class="value">${r.final.levels_completed}/4 ${levelDots(r.final.levels_completed, 4, firstOver)}</div>
        <div class="sub">${stopNote(r.final)}</div></div>
      <div class="stat"><div class="label">Time used</div>
        <div class="value">${fmtClock(Math.min(r.elapsed, r.time_limit))}</div>
        <div class="sub">${r.overtime_seconds > 0 ? `+ ${fmtClock(r.overtime_seconds)} overtime` : `of ${fmtClock(r.time_limit)}`}</div></div>
      <div class="stat"><div class="label">Pauses</div>
        <div class="value">${r.pauses.count}</div>
        <div class="sub">${r.pauses.count ? `${fmtClock(r.pauses.total_seconds)} paused` : data.mode === "strict" ? "strict mode" : "none taken"} · ${plural(r.runs, "run")} · ${plural(r.submits, "submit")}</div></div>
    </div>
    <h2 class="section-title">Pacing</h2>
    <table class="table"><tr><th>Level</th><th>Target</th><th>Passed at</th><th>Time on level</th><th>vs target</th><th></th></tr>${pacingRows}</table>
    <div class="review-tabs">
      <div class="tabs" data-review-tabs></div>
      <div data-review-panel></div>
    </div>
  </main>`;

  const tabs = [
    ["analysis", "Solution analysis"],
    ["hints", "Design hints"],
    ["reference", "Reference solution"],
    ["yours", "Your code"],
    ["statement", "Full problem"],
    ["timeline", "Timeline"],
  ];
  let current = "analysis";
  let viewer = null;
  const panel = $app.querySelector("[data-review-panel]");

  async function show(key) {
    current = key;
    if (viewer) { viewer.dispose(); viewer = null; }
    $app.querySelector("[data-review-tabs]").innerHTML = tabs.map(([k, label]) =>
      `<button class="tab ${k === current ? "active" : ""}" data-k="${k}">${label}</button>`).join("");
    $app.querySelectorAll("[data-k]").forEach((b) => { b.onclick = () => show(b.dataset.k); });
    if (key === "reference" || key === "yours") {
      panel.className = "review-panel code";
      panel.innerHTML = "";
      const code = key === "reference" ? (data.reference_code ?? "# No reference solution available.") : data.code;
      const monaco = await window.monacoReady;
      if (current !== key) return;
      viewer = monaco.editor.create(panel, {
        value: code, language: "python", theme: "vs-dark", readOnly: true, automaticLayout: true,
        minimap: { enabled: false }, fontSize: 13, scrollBeyondLastLine: false,
      });
      return;
    }
    panel.className = "review-panel md";
    if (key === "analysis") panel.innerHTML = data.analysis_html;
    else if (key === "hints") panel.innerHTML = data.hints_html;
    else if (key === "statement") {
      panel.innerHTML = `<details class="conventions" style="margin:0 0 18px"><summary>Conventions</summary><div class="md">${data.conventions_html}</div></details>`
        + data.levels.map((l) => `<div class="level-block"><h3>Level ${l.level}: ${esc(l.title)}</h3>${l.statement_html}</div>`).join("");
    } else if (key === "timeline") {
      panel.innerHTML = renderTimeline(data);
    }
  }
  show(current);
  cleanup = async () => { if (viewer) viewer.dispose(); };
}

function renderTimeline(data) {
  const events = [];
  for (const s of data.submissions) {
    const counts = s.breakdown[String(s.level)];
    const own = counts
      ? `L${s.level}: shown ${counts.shown_passed}/${counts.shown_total}` + (s.kind === "submit" ? `, hidden ${counts.hidden_passed}/${counts.hidden_total}` : "")
      : "";
    events.push({ t: s.elapsed, html: `<td>${s.kind === "submit" ? "<strong>Submit</strong>" : "Run"}</td><td>${own}</td>
      <td class="${s.all_passed ? "pass" : "fail"}">${s.all_passed ? "all passed" : "failing"}</td><td>${s.lint_count} lint</td>` });
  }
  for (const p of data.pauses) {
    const dur = (p.ended_at ?? p.started_at) - p.started_at;
    events.push({ t: p.start_elapsed, html: `<td class="warn">Pause</td><td>${fmtClock(dur)}</td><td></td><td></td>` });
  }
  for (const lv of data.results.levels) {
    if (lv.completed_at != null) {
      events.push({ t: lv.completed_at + 0.001, html: `<td class="pass"><strong>Level ${lv.level} passed</strong></td><td></td><td>${lv.overtime ? '<span class="warn">overtime</span>' : ""}</td><td></td>` });
    }
  }
  events.sort((a, b) => a.t - b.t);
  if (!events.length) return '<p class="dim">No runs or submits in this session.</p>';
  return `<table class="table"><tr><th>At</th><th>Event</th><th>Detail</th><th>Result</th><th>Lint</th></tr>
    ${events.map((e) => `<tr><td class="mono">${fmtClock(e.t)}</td>${e.html}</tr>`).join("")}</table>`;
}

// ---------------------------------------------------------------- history
async function renderHistory() {
  const { sessions } = await api("GET", "/api/history");
  const rows = sessions.map((s) => `<tr class="clickable" data-id="${s.id}" data-status="${s.status}">
      <td>${fmtDate(s.started_at)}</td>
      <td>${esc(s.problem_title)}</td>
      <td>${s.mode}</td>
      <td>${s.status === "active" ? '<span class="chip">in progress</span>' : `${levelDots(s.timed_levels)} ${s.timed_levels}/4`}</td>
      <td>${s.status === "active" ? "—" : `${s.final_levels}/4`}</td>
      <td>${fmtClock(Math.min(s.elapsed, 5400))}${s.elapsed > 5400 ? ` <span class="warn">+${fmtClock(s.elapsed - 5400)}</span>` : ""}</td>
      <td>${s.pauses.count ? `${s.pauses.count} (${fmtClock(s.pauses.total_seconds)})` : "—"}</td>
    </tr>`).join("");
  $app.innerHTML = `${topnav("history")}<main class="page">
    <h1>History</h1>
    <p class="lead">Every attempt, newest first. Open one to see its results, pacing, hints and your final code.</p>
    ${sessions.length ? `<table class="table"><tr><th>Date</th><th>Problem</th><th>Mode</th><th>Timed levels</th><th>Incl. overtime</th><th>Time</th><th>Pauses</th></tr>${rows}</table>`
      : '<p class="dim">No attempts yet. <a href="#/">Start one</a>.</p>'}
  </main>`;
  $app.querySelectorAll("tr[data-id]").forEach((tr) => {
    tr.onclick = () => {
      location.hash = tr.dataset.status === "active" ? `#/session/${tr.dataset.id}` : `#/review/${tr.dataset.id}`;
    };
  });
}

route();
