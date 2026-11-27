// SWE Practice frontend: hash-routed single page. The home page picks a track; this file holds the
// router and the coding pages (problems, session, review, study, history). Algorithms live in
// algo.js, system design in design.js, the foundations and tech pages in learn.js, the tech
// projects' file browser in files.js, shared helpers in common.js.

import {
  $app, $modalRoot, STARTING_PYTHON, api, esc, fmtClock, fmtDelta, plural, fmtDate, storage, toast,
  modal, chooseMode, confirmSpoil, topnav, levelDots, dragGutter, resizableSplit, watchDiagrams,
  lintSeverity, historyBackupSection, bindHistoryBackup,
} from "./common.js";
import { coolDown, warmUp } from "./backend.js";
import {
  renderDesignHome, renderDesignSession, renderDesignReview, renderDesignStudy, renderFramework,
  designHistoryTable, designTrackCard,
} from "./design.js";
import {
  renderAlgoHome, renderAlgoSession, renderAlgoReview, renderAlgoProblem, algoHistoryTable,
  algoTrackCard,
} from "./algo.js";
import { renderLearn, techTrackCard } from "./learn.js";
import { renderFiles } from "./files.js";

// ---------------------------------------------------------------- router
let cleanup = null;

// [hash pattern, page]; captured groups are passed to the page. A page may return its cleanup.
const ROUTES = [
  [/^#\/?$/, renderHome],
  [/^#\/coding$/, renderCodingHome],
  [/^#\/session\/(\d+)$/, (id) => renderSession(Number(id))],
  [/^#\/review\/(\d+)$/, (id) => renderReview(Number(id))],
  [/^#\/problem\/([\w-]+)\/(question|hints|reference)$/, renderStudy],
  [/^#\/history$/, renderHistory],
  [/^#\/design$/, renderDesignHome],
  [/^#\/design\/framework$/, renderFramework],
  [/^#\/design\/session\/(\d+)$/, (id) => renderDesignSession(Number(id))],
  [/^#\/design\/review\/(\d+)$/, (id) => renderDesignReview(Number(id))],
  [/^#\/design\/question\/([\w-]+)\/(hints|reference)$/, renderDesignStudy],
  [/^#\/design\/learn(?:\/([\w-]+))?(?:\/([\w-]+))?$/, (slug, section) => renderLearn("design", slug, section)],
  [/^#\/algo$/, renderAlgoHome],
  [/^#\/algo\/session\/(\d+)$/, (id) => renderAlgoSession(Number(id))],
  [/^#\/algo\/review\/(\d+)$/, (id) => renderAlgoReview(Number(id))],
  [/^#\/algo\/problem\/([\w-]+)(?:\/(question|hints|solution))?$/, renderAlgoProblem],
  [/^#\/algo\/learn(?:\/([\w-]+))?(?:\/([\w-]+))?$/, (slug, section) => renderLearn("algo", slug, section)],
  // Before the next route, which would take "files" for a section id.
  [/^#\/tech\/([\w-]+)\/files(?:\/(.+))?$/, renderFiles],
  [/^#\/tech(?:\/([\w-]+))?(?:\/([\w-]+))?$/, (slug, section) => renderLearn("tech", slug, section)],
];

async function route() {
  if (cleanup) { await cleanup(); cleanup = null; }
  $modalRoot.innerHTML = "";
  const hash = location.hash || "#/";
  try {
    for (const [pattern, page] of ROUTES) {
      const m = hash.match(pattern);
      if (!m) continue;
      const done = await page(...m.slice(1));
      if (typeof done === "function") cleanup = done;
      return;
    }
    await renderHome();
  } catch (err) {
    $app.innerHTML = `${topnav("")}<div class="page"><div class="callout bad">${esc(err.message)}</div>
      <a href="#/">Back to the home page</a></div>`;
  }
}
window.addEventListener("hashchange", route);

// ---------------------------------------------------------------- home: pick a track
async function renderHome() {
  const [coding, codingActive, algoCard, designCard, techCard] = await Promise.all([
    api("GET", "/api/problems"), api("GET", "/api/active"), algoTrackCard(), designTrackCard(),
    techTrackCard(),
  ]);
  const active = codingActive.session;
  const attempts = coding.problems.reduce((sum, p) => sum + p.attempts, 0);
  const status = active
    ? `<span class="chip good">In progress: ${esc(active.problem.title)} · ${active.timer.paused ? "paused"
      : active.timer.overtime ? "overtime" : `${fmtClock(active.timer.remaining)} left`}</span>`
    : `<span class="faint">${attempts ? `${plural(attempts, "attempt")} so far` : "No attempts yet"}</span>`;

  $app.innerHTML = `${topnav("home")}<main class="page">
    <h1>Interview practice</h1>
    <p class="lead">Three kinds of timed practice, run the way the real rounds are, and deep dives into
      specific technologies. Pick one.</p>
    <div class="track-grid">
      <a class="track-card" href="#/coding">
        <div class="track-head"><span class="track-mark">&lt;/&gt;</span><h2>Coding assessment</h2></div>
        <p>90 minutes, one problem in four levels, revealed one at a time. You write Python against
          shown and hidden tests, and each level unlocks when everything up to it passes.</p>
        <ul class="track-facts"><li>${plural(coding.problems.length, "problem")}</li><li>${coding.time_limit / 60} min</li><li>auto-graded</li></ul>
        <div class="track-foot">${status}<span class="track-cta">Open →</span></div>
      </a>
      ${algoCard}
      ${designCard}
      ${techCard}
    </div>
  </main>`;
}

// ---------------------------------------------------------------- coding: problem list
async function renderCodingHome() {
  const [{ problems }, { session: active }] = await Promise.all([
    api("GET", "/api/problems"), api("GET", "/api/active"),
  ]);
  const preferUnseen = storage("swe-prac-prefer-unseen") !== "0";

  const banner = active ? `<div class="banner">
      <div><strong>Session in progress:</strong> ${esc(active.problem.title)} ·
        ${active.mode} · Level ${Math.min(active.current_level, 4)} ·
        <span class="mono">${active.timer.paused ? "paused" : active.timer.overtime ? "overtime" : fmtClock(active.timer.remaining) + " left"}</span></div>
      <div style="display:flex;gap:8px"><button class="primary" data-resume>Resume</button>
        <button class="danger" data-end-active>End session</button></div>
    </div>` : "";

  const studyViews = [["question", "Question"], ["hints", "Hints"], ["reference", "Reference solution"]];
  const cards = problems.map((p) => {
    // While a session on this problem is running, its spoilers stay shut.
    const inSession = active && active.problem.id === p.id;
    const studyButtons = studyViews.map(([view, label]) =>
      `<button class="small" data-study="${view}" data-pid="${esc(p.id)}" ${inSession ? 'disabled title="Locked while this problem is in a running session"' : ""}>${label}</button>`,
    ).join("");
    return `<article class="problem-card">
      <span class="num">PROBLEM ${p.number}</span>
      <h3>${esc(p.title)}</h3>
      <p>${esc(p.summary)}</p>
      <div class="study-links">${studyButtons}</div>
      <div class="meta">
        <span class="dim" style="font-size:12px">${p.attempts ? `${p.attempts} attempt${p.attempts > 1 ? "s" : ""} · best ${levelDots(p.best_timed_levels || 0)}` : "Not attempted"}</span>
        <button class="primary small" data-start="${esc(p.id)}" ${active ? "disabled" : ""}>Start</button>
      </div>
    </article>`;
  }).join("");

  $app.innerHTML = `${topnav("coding")}<main class="page">
    <h1>90-minute coding assessment practice</h1>
    <p class="lead">One problem, four levels, revealed one at a time. Each level unlocks when every shown and hidden test up to it passes.</p>
    ${banner}
    <h2 class="section-title">Problems</h2>
    <div class="random-row">
      <button data-random ${active ? "disabled" : ""}>🎲 Start a random problem</button>
      <label><input type="checkbox" data-unseen ${preferUnseen ? "checked" : ""}> Prefer problems I haven't tried</label>
    </div>
    <div class="problem-grid">${cards || '<p class="dim">No problems are built yet. Run <code>tools/build_problem.py --all</code>.</p>'}</div>
  </main>`;

  const unseenBox = $app.querySelector("[data-unseen]");
  unseenBox.addEventListener("change", () => storage("swe-prac-prefer-unseen", unseenBox.checked ? "1" : "0"));

  const start = async (problemId) => {
    const mode = await chooseMode(90, "Level 1 only");
    if (!mode) return;
    try {
      const s = await api("POST", "/api/sessions", {
        problem_id: problemId, mode, prefer_unseen: unseenBox.checked,
      });
      location.hash = `#/session/${s.id}`;
    } catch (err) { toast(err.message, "bad"); }
  };
  $app.querySelectorAll("[data-start]").forEach((b) => b.addEventListener("click", () => start(b.dataset.start)));
  $app.querySelectorAll("[data-study]").forEach((b) => b.addEventListener("click", async () => {
    const problem = problems.find((p) => p.id === b.dataset.pid);
    if (!problem.attempts && !(await confirmSpoil(problem.title, "question, hints or reference solution"))) return;
    location.hash = `#/problem/${b.dataset.pid}/${b.dataset.study}`;
  }));
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
  warmUp(); // load Python and ruff now, so the first Run doesn't wait for them
  const monaco = await window.monacoReady;

  const st = {
    session,
    timer: { ...session.timer, syncedAt: performance.now() },
    selectedLevel: Math.min(session.current_level, 4),
    file: "solution",
    resultsTab: "tests",
    busy: false,
    busyText: "Running…",
    dirty: false,
    lastSaved: null,
    lastResult: null,
    lint: { issues: [], error: null },
    scratchOut: null,
    timeUpShown: storage(`swe-prac-timeup-${sessionId}`) === "1",
  };

  $app.innerHTML = `<div class="session">
    <div class="session-bar">
      <a href="#/coding" class="ghost" title="Back to problems" style="color:var(--text-dim)">←</a>
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
    // While readOnly is set, also mark the hidden textarea readonly so mobile keeps its keyboard closed.
    domReadOnly: true,
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

  async function save() {
    if (!st.dirty || st.timer.paused) return;
    const body = { code: solutionModel.getValue(), scratch: scratchModel.getValue() };
    st.dirty = false;
    try {
      const res = await api("PUT", `/api/sessions/${sessionId}/code`, body);
      st.lastSaved = Date.now();
      if (res?.timer) syncTimer(res.timer);
    } catch (err) {
      st.dirty = true;
      if (err.status !== 409) toast(`Autosave failed: ${err.message}`, "bad");
    }
    renderSaveState();
  }
  const autosave = setInterval(save, 3000);
  const beforeUnload = () => { save(); };
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
      severity: lintSeverity(monaco, i.code),
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
    if (st.busy) { el.innerHTML = `<div class="empty">${esc(st.busyText)}</div>`; return; }
    if (st.resultsTab === "scratch") { el.innerHTML = renderScratch(); return; }
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
        <span class="chip ${o.exit_code === 0 ? "good" : "bad"}">${o.timed_out ? "timed out" : o.crashed ? "crashed" : `exit ${o.exit_code}`}</span>
        <span class="faint">${o.ms} ms</span></div>
      <div class="block-label">stdout</div><pre class="out">${esc(o.stdout) || '<span class="faint">(empty)</span>'}</pre>
      ${o.stderr ? `<div class="block-label">stderr</div><pre class="out fail">${esc(o.stderr)}</pre>` : ""}`;
  }

  // ----- actions
  function setBusy(busy) {
    st.busy = busy;
    st.busyText = "Running…";
    q("[data-run]").disabled = q("[data-submit]").disabled = q("[data-scratch]").disabled = busy || st.timer.paused;
  }

  // While a run waits for Python to load (the first one in this browser downloads it), say so.
  const onPython = (e) => {
    if (!st.busy) return;
    st.busyText = e.detail.state === "loading" ? STARTING_PYTHON : "Running…";
    renderResults();
  };
  window.addEventListener("swe-python", onPython);

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
    st.resultsTab = "scratch";
    renderResultTabs();
    renderResults();
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
  const savedBottom = storage("swe-prac-bottom-height");
  if (savedBottom) q(".code-pane").style.setProperty("--bottom-height", savedBottom);
  resizableSplit(workspace, q("[data-gutter-x]"));
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
    await save();
    clearInterval(autosave); clearInterval(tick); clearInterval(resync); clearTimeout(lintTimer);
    window.removeEventListener("beforeunload", beforeUnload);
    window.removeEventListener("keydown", keyHandler);
    window.removeEventListener("swe-python", onPython);
    coolDown();
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
        value: code, language: "python", theme: "vs-dark", readOnly: true, domReadOnly: true, automaticLayout: true,
        minimap: { enabled: false }, fontSize: 13, scrollBeyondLastLine: false,
      });
      return;
    }
    panel.className = "review-panel md";
    if (key === "analysis") panel.innerHTML = data.analysis_html;
    else if (key === "hints") panel.innerHTML = data.hints_html;
    else if (key === "statement") {
      panel.innerHTML = fullStatementHtml(data);
    } else if (key === "timeline") {
      panel.innerHTML = renderTimeline(data);
    }
  }
  show(current);
  cleanup = async () => { if (viewer) viewer.dispose(); };
}

// All four levels of a problem plus the shared conventions (review page and problem study page).
function fullStatementHtml({ conventions_html, levels }) {
  return `<details class="conventions" style="margin:0 0 18px"><summary>Conventions</summary><div class="md">${conventions_html}</div></details>`
    + levels.map((l) => `<div class="level-block"><h3>Level ${l.level}: ${esc(l.title)}</h3>${l.statement_html}</div>`).join("");
}

// ---------------------------------------------------------------- problem study
// Question / hints / reference solution for one problem, opened from the home cards.
async function renderStudy(problemId, kind) {
  const data = await api("GET", `/api/problems/${encodeURIComponent(problemId)}/${kind}`);
  const tabs = [["question", "Question"], ["hints", "Hints"], ["reference", "Reference solution"]];
  $app.innerHTML = `${topnav("coding")}<main class="page">
    <p class="faint" style="margin:0 0 4px"><a href="#/coding">← Problems</a></p>
    <h1>${esc(data.problem.title)}</h1>
    <p class="lead">${esc(data.problem.summary)}</p>
    <div class="review-tabs" style="margin-top:0">
      <div class="tabs">${tabs.map(([k, label]) =>
        `<a class="tab ${k === kind ? "active" : ""}" href="#/problem/${esc(problemId)}/${k}">${label}</a>`).join("")}</div>
      <div data-study-panel></div>
    </div>
  </main>`;
  const panel = $app.querySelector("[data-study-panel]");

  if (kind === "reference") {
    panel.className = "review-panel code";
    let viewer = null;
    cleanup = async () => viewer?.dispose();
    const monaco = await window.monacoReady;
    if (!panel.isConnected) return;  // navigated away while Monaco was loading
    viewer = monaco.editor.create(panel, {
      value: data.reference_code ?? "# No reference solution available.",
      language: "python", theme: "vs-dark", readOnly: true, domReadOnly: true, automaticLayout: true,
      minimap: { enabled: false }, fontSize: 13, scrollBeyondLastLine: false,
    });
    return;
  }
  panel.className = "review-panel md";
  panel.innerHTML = kind === "question" ? fullStatementHtml(data) : data.hints_html;
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

// ---------------------------------------------------------------- history (every track)
async function renderHistory() {
  const [{ sessions }, algoTable, designTable] = await Promise.all([
    api("GET", "/api/history"), algoHistoryTable(), designHistoryTable(),
  ]);
  const rows = sessions.map((s) => `<tr class="clickable" data-href="${s.status === "active" ? `#/session/${s.id}` : `#/review/${s.id}`}">
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
    <p class="lead">Every attempt, newest first. Open one to see its results, pacing and your final work.</p>
    <h2 class="section-title">Coding</h2>
    ${sessions.length ? `<table class="table"><tr><th>Date</th><th>Problem</th><th>Mode</th><th>Timed levels</th><th>Incl. overtime</th><th>Time</th><th>Pauses</th></tr>${rows}</table>`
      : '<p class="dim">No coding attempts yet. <a href="#/coding">Start one</a>.</p>'}
    <h2 class="section-title">Algorithms</h2>
    ${algoTable}
    <h2 class="section-title">System design</h2>
    ${designTable}
    ${historyBackupSection()}
  </main>`;
  $app.querySelectorAll("tr[data-href]").forEach((tr) => {
    tr.onclick = () => { location.hash = tr.dataset.href; };
  });
  bindHistoryBackup(renderHistory);
}

watchDiagrams();
route();
