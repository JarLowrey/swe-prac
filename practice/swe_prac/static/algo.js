// Algorithm practice: the problem list (with the foundations pages), the timed session (editor,
// Run on the examples, Submit with the hidden tests), the review (explanation, hints, reference
// solution), the problem and study pages, and the history table. Pages return their cleanup.

import {
  $app, STARTING_PYTHON, api, esc, fmtClock, plural, fmtDate, storage, toast, modal, chooseMode,
  confirmSpoil, topnav, dragGutter, resizableSplit, lintSeverity,
} from "./common.js";
import { coolDown, warmUp } from "./backend.js";
import { foundationsSection } from "./learn.js";

const DIFFICULTIES = ["Easy", "Medium", "Hard"];
const STUDY_VIEWS = [["question", "Question"], ["hints", "Hints"], ["solution", "Solution"]];
const timerLabel = (t) => (t.paused ? "paused" : t.overtime ? "overtime" : `${fmtClock(t.remaining)} left`);
const diffChip = (d) => `<span class="diff ${esc(String(d).toLowerCase())}">${esc(d)}</span>`;

// Python's repr of JSON test data, so inputs and expected values read like the runner's output.
function py(value) {
  if (value === null || value === undefined) return "None";
  if (value === true) return "True";
  if (value === false) return "False";
  if (typeof value === "string") {
    const quote = value.includes("'") && !value.includes('"') ? '"' : "'";
    const body = value.replace(/\\/g, "\\\\").replace(/\n/g, "\\n").replace(/\t/g, "\\t");
    return quote + (quote === "'" ? body.replace(/'/g, "\\'") : body) + quote;
  }
  if (Array.isArray(value)) return `[${value.map(py).join(", ")}]`;
  if (typeof value === "object") {
    const keys = Object.keys(value);
    if (keys.length === 1 && keys[0] === "__tuple__") {
      const items = value.__tuple__.map(py);
      return `(${items.join(", ")}${items.length === 1 ? "," : ""})`;
    }
    return `{${Object.entries(value).map(([k, v]) => `${py(k)}: ${py(v)}`).join(", ")}}`;
  }
  return String(value);
}

const argsText = (params, args) => args.map((a, i) => `${params[i] ?? `arg${i + 1}`} = ${py(a)}`).join(", ");

function resultLabel(part, limit) {
  if (part.solved) return '<span class="pass">✓ Solved</span>';
  const b = part.best;
  return b ? `${b.passed}/${b.total} tests` : '<span class="faint">no submit</span>';
}

function foundationChips(links, label = "Foundations to review") {
  if (!links?.length) return "";
  const chips = links.map((f) => `<a class="chip link" href="${esc(f.href)}">${esc(f.title)}
    <span class="faint">· ${esc(f.page_title)}</span></a>`).join(" ");
  return `<div class="callout info hint-box"><div><strong>${label}:</strong> ${chips}</div></div>`;
}

function confirmEnd() {
  return modal({
    title: "End this session?",
    body: "<p>Your code and score lock, and the hints and explained solution unlock.</p>",
    actions: [{ label: "Keep working", value: false, kind: "ghost" }, { label: "End & review", value: true, kind: "primary" }],
  });
}

async function startSession(body, minutes) {
  const mode = await chooseMode(
    minutes ?? "timed", "the problem statement",
    minutes ? undefined : "Start a random problem?",
  );
  if (!mode) return;
  try {
    const s = await api("POST", "/api/algo/sessions", { ...body, mode });
    location.hash = `#/algo/session/${s.id}`;
  } catch (err) { toast(err.message, "bad"); }
}

// ---------------------------------------------------------------- home page card
export async function algoTrackCard() {
  const [{ problems, minutes }, { session: active }] = await Promise.all([
    api("GET", "/api/algo/problems"), api("GET", "/api/algo/active"),
  ]);
  const attempts = problems.reduce((sum, p) => sum + p.attempts, 0);
  const solved = problems.filter((p) => p.solved).length;
  const status = active
    ? `<span class="chip good">In progress: ${esc(active.problem.title)} · ${timerLabel(active.timer)}</span>`
    : `<span class="faint">${attempts ? `${plural(attempts, "attempt")} · ${solved} solved` : "No attempts yet"}</span>`;
  return `<a class="track-card" href="#/algo">
    <div class="track-head"><span class="track-mark algo">{ }</span><h2>Algorithms</h2></div>
    <p>Classic interview problems in Python. Hidden tests include inputs only an efficient algorithm
      finishes in time. Explanations and foundations pages follow.</p>
    <ul class="track-facts"><li>${plural(problems.length, "problem")}</li><li>${minutes.Easy}–${minutes.Hard} min</li><li>auto-graded</li></ul>
    <div class="track-foot">${status}<span class="track-cta">Open →</span></div>
  </a>`;
}

// ---------------------------------------------------------------- problem list
export async function renderAlgoHome() {
  const [{ problems, minutes, patterns }, { session: active }, foundations] = await Promise.all([
    api("GET", "/api/algo/problems"), api("GET", "/api/algo/active"),
    foundationsSection("algo", "Approach, Big O, data structures, patterns and dynamic programming."),
  ]);
  const f = {
    q: "",
    difficulty: storage("swe-prac-algo-difficulty") ?? "",
    pattern: storage("swe-prac-algo-pattern") ?? "",
    status: storage("swe-prac-algo-status") ?? "",
  };
  if (!patterns.includes(f.pattern)) f.pattern = "";
  const showPatterns = storage("swe-prac-algo-show-patterns") !== "0";
  const preferUnseen = storage("swe-prac-algo-prefer-unseen") !== "0";

  const banner = active ? `<div class="banner">
      <div><strong>Session in progress:</strong> ${esc(active.problem.title)} · ${active.mode} ·
        <span class="mono">${timerLabel(active.timer)}</span>${active.solved_at != null ? ' · <span class="pass">solved</span>' : ""}</div>
      <div style="display:flex;gap:8px"><button class="primary" data-resume>Resume</button>
        <button class="danger" data-end-active>End session</button></div>
    </div>` : "";
  const option = (value, label, current) => `<option value="${esc(value)}" ${value === current ? "selected" : ""}>${esc(label)}</option>`;

  $app.innerHTML = `${topnav("algo")}<main class="page">
    <h1>Algorithm interview practice</h1>
    <p class="lead">${minutes.Easy} minutes for Easy, ${minutes.Medium} for Medium, ${minutes.Hard} for Hard.
      <strong>Run</strong> checks the examples; <strong>Submit</strong> adds hidden tests, including inputs only an
      efficient algorithm finishes in time. Hints and the explained solution open when the session ends.</p>
    ${banner}
    ${foundations}
    <h2 class="section-title">Problems</h2>
    <div class="filter-row">
      <input type="search" placeholder="Search titles" data-filter="q" aria-label="Search titles">
      <select data-filter="difficulty" aria-label="Difficulty">${option("", "All difficulties", f.difficulty)}${DIFFICULTIES.map((d) => option(d, d, f.difficulty)).join("")}</select>
      <select data-filter="pattern" aria-label="Pattern">${option("", "All patterns", f.pattern)}${patterns.map((p) => option(p, p, f.pattern)).join("")}</select>
      <select data-filter="status" aria-label="Status">${option("", "Any status", f.status)}${option("new", "Not attempted", f.status)}${option("unsolved", "Attempted, not solved", f.status)}${option("solved", "Solved", f.status)}</select>
      <label class="dim"><input type="checkbox" data-show-patterns ${showPatterns ? "checked" : ""}> Show patterns</label>
      <span class="faint" data-count></span>
    </div>
    <div class="random-row">
      <button data-random ${active ? "disabled" : ""}>🎲 Random problem</button>
      <span class="faint">within the filters</span>
      <label><input type="checkbox" data-unseen ${preferUnseen ? "checked" : ""}> Prefer problems I haven't tried</label>
    </div>
    <div class="problem-grid ${showPatterns ? "" : "hide-patterns"}" data-grid></div>
  </main>`;

  const q = (sel) => $app.querySelector(sel);
  const grid = q("[data-grid]");

  const card = (p) => {
    const inSession = active && active.problem.id === p.id;
    const lock = inSession ? 'disabled title="Locked during a session on this problem"' : "";
    const status = p.solved
      ? `<span class="pass">✓ Solved${p.solved_in_time ? "" : " in overtime"}</span> · ${plural(p.attempts, "attempt")}`
      : p.attempts ? `${plural(p.attempts, "attempt")} · not solved yet` : "Not attempted";
    return `<article class="problem-card algo-card">
      <div class="card-top"><span class="num">#${p.number}</span>${diffChip(p.difficulty)}<span class="faint">${p.minutes} min</span></div>
      <h3><a href="#/algo/problem/${esc(p.id)}">${esc(p.title)}</a></h3>
      <div class="pattern-chips">${p.patterns.map((x) => `<span class="chip">${esc(x)}</span>`).join("")}</div>
      <div class="study-links">${STUDY_VIEWS.map(([view, label]) =>
        `<button class="small" data-study="${view}" data-pid="${esc(p.id)}" ${lock}>${label}</button>`).join("")}</div>
      <div class="meta">
        <span class="dim" style="font-size:12px">${status}</span>
        <button class="primary small" data-start="${esc(p.id)}" ${active ? "disabled" : ""}>Start</button>
      </div>
    </article>`;
  };

  function matches(p) {
    if (f.q && !p.title.toLowerCase().includes(f.q.toLowerCase())) return false;
    if (f.difficulty && p.difficulty !== f.difficulty) return false;
    if (f.pattern && !p.patterns.includes(f.pattern)) return false;
    if (f.status === "new" && p.attempts) return false;
    if (f.status === "unsolved" && (!p.attempts || p.solved)) return false;
    if (f.status === "solved" && !p.solved) return false;
    return true;
  }

  function renderGrid() {
    const shown = problems.filter(matches);
    q("[data-count]").textContent = `${shown.length} of ${problems.length}`;
    grid.innerHTML = shown.map(card).join("") || (problems.length
      ? '<p class="dim">No problem matches these filters.</p>'
      : '<p class="dim">No problems are built yet. Run <code>tools/build_algo.py</code>.</p>');
    grid.querySelectorAll("[data-start]").forEach((b) => {
      const p = problems.find((x) => x.id === b.dataset.start);
      b.onclick = () => startSession({ problem_id: p.id }, p.minutes);
    });
    grid.querySelectorAll("[data-study]").forEach((b) => {
      b.onclick = async () => {
        const p = problems.find((x) => x.id === b.dataset.pid);
        if (!p.attempts && !(await confirmSpoil(p.title, "question, hints or solution"))) return;
        location.hash = `#/algo/problem/${p.id}/${b.dataset.study}`;
      };
    });
  }

  $app.querySelectorAll("[data-filter]").forEach((el) => {
    el.addEventListener("input", () => {
      f[el.dataset.filter] = el.value;
      if (el.dataset.filter !== "q") storage(`swe-prac-algo-${el.dataset.filter}`, el.value);
      renderGrid();
    });
  });
  const patternsBox = q("[data-show-patterns]");
  patternsBox.addEventListener("change", () => {
    grid.classList.toggle("hide-patterns", !patternsBox.checked);
    storage("swe-prac-algo-show-patterns", patternsBox.checked ? "1" : "0");
  });
  const unseenBox = q("[data-unseen]");
  unseenBox.addEventListener("change", () => storage("swe-prac-algo-prefer-unseen", unseenBox.checked ? "1" : "0"));
  q("[data-random]").addEventListener("click", () => startSession({
    problem_id: null,
    difficulty: f.difficulty || null,
    pattern: f.pattern || null,
    prefer_unseen: unseenBox.checked,
  }, f.difficulty ? minutes[f.difficulty] : null));
  q("[data-resume]")?.addEventListener("click", () => { location.hash = `#/algo/session/${active.id}`; });
  q("[data-end-active]")?.addEventListener("click", async () => {
    if (!(await confirmEnd())) return;
    await api("POST", `/api/algo/sessions/${active.id}/end`);
    location.hash = `#/algo/review/${active.id}`;
  });
  renderGrid();
  return undefined;
}

// ---------------------------------------------------------------- one problem: overview and study views
// #/algo/problem/<id> is where links from explanations and foundations pages land: it offers a timed
// attempt first and keeps the spoilers one (confirmed) click away. With a view it shows the
// question, the hints or the explained solution.
export async function renderAlgoProblem(problemId, kind) {
  if (!kind) return renderOverview(problemId);
  const data = await api("GET", `/api/algo/problems/${encodeURIComponent(problemId)}/${kind}`);
  const p = data.problem;
  $app.innerHTML = `${topnav("algo")}<main class="page">
    <p class="faint" style="margin:0 0 4px"><a href="#/algo">← Algorithms</a> · <a href="#/algo/problem/${esc(p.id)}">Problem overview</a></p>
    <h1>${esc(p.title)}</h1>
    <p class="lead">${diffChip(p.difficulty)} <span class="faint">#${p.number} · ${p.minutes} min ·
      ${p.patterns.map(esc).join(", ")}</span></p>
    <div class="review-tabs" style="margin-top:0">
      <div class="tabs">${STUDY_VIEWS.map(([k, label]) =>
        `<a class="tab ${k === kind ? "active" : ""}" href="#/algo/problem/${esc(p.id)}/${k}">${label}</a>`).join("")}</div>
      <div class="review-panel md algo-study" data-panel></div>
    </div>
  </main>`;
  const panel = $app.querySelector("[data-panel]");
  if (kind === "question") {
    panel.innerHTML = data.statement_html;
  } else if (kind === "hints") {
    panel.innerHTML = foundationChips(data.foundations) + data.hints_html;
  } else {
    panel.innerHTML = foundationChips(data.foundations) + data.explanation_html;
  }
  return undefined;
}

async function renderOverview(problemId) {
  const [{ problems }, { session: active }, { sessions }] = await Promise.all([
    api("GET", "/api/algo/problems"), api("GET", "/api/algo/active"), api("GET", "/api/algo/history"),
  ]);
  const p = problems.find((x) => x.id === problemId);
  if (!p) throw new Error(`Unknown problem ${problemId}`);
  const mine = sessions.filter((s) => s.problem_id === p.id);
  const inSession = active && active.problem.id === p.id;
  const lock = inSession ? 'disabled title="Locked during a session on this problem"' : "";
  $app.innerHTML = `${topnav("algo")}<main class="page">
    <p class="faint" style="margin:0 0 4px"><a href="#/algo">← Algorithms</a></p>
    <h1>${esc(p.title)}</h1>
    <p class="lead">${diffChip(p.difficulty)} <span class="faint">#${p.number} · ${p.minutes}-minute session ·
      ${p.patterns.map(esc).join(", ")}</span></p>
    ${inSession ? `<div class="banner"><div><strong>Session in progress</strong> ·
      <span class="mono">${timerLabel(active.timer)}</span></div><button class="primary" data-resume>Resume</button></div>` : ""}
    <div class="overview-actions">
      <button class="primary" data-start ${active ? "disabled" : ""}>Start a timed attempt</button>
      ${STUDY_VIEWS.map(([view, label]) => `<button data-study="${view}" ${lock}>${label}</button>`).join("")}
    </div>
    <p class="dim">${p.attempts ? "" : "Not attempted yet. Try it cold and timed first; the spoilers will still be here."}</p>
    <h2 class="section-title">Your attempts</h2>
    ${mine.length ? historyTable(mine, false) : '<p class="dim">None yet.</p>'}
  </main>`;
  const q = (sel) => $app.querySelector(sel);
  q("[data-start]").onclick = () => startSession({ problem_id: p.id }, p.minutes);
  q("[data-resume]")?.addEventListener("click", () => { location.hash = `#/algo/session/${active.id}`; });
  $app.querySelectorAll("[data-study]").forEach((b) => {
    b.onclick = async () => {
      if (!p.attempts && !(await confirmSpoil(p.title, "question, hints or solution"))) return;
      location.hash = `#/algo/problem/${p.id}/${b.dataset.study}`;
    };
  });
  bindRows();
  return undefined;
}

// ---------------------------------------------------------------- session
export async function renderAlgoSession(sessionId) {
  let session;
  try {
    session = await api("GET", `/api/algo/sessions/${sessionId}`);
  } catch (err) {
    if (err.status === 410) { location.hash = `#/algo/review/${sessionId}`; return undefined; }
    throw err;
  }
  warmUp(); // load Python and ruff now, so the first Run doesn't wait for them
  const monaco = await window.monacoReady;
  const examples = Object.fromEntries(session.examples.map((e) => [e.id, e]));
  const st = {
    timer: { ...session.timer, syncedAt: performance.now() },
    solvedAt: session.solved_at,
    file: "solution",
    resultsTab: "tests",
    busy: false,
    busyText: "Running…",
    dirty: false,
    lastSaved: null,
    lastResult: null,
    lint: { issues: [], error: null },
    scratchOut: null,
    timeUpShown: storage(`swe-prac-algo-timeup-${sessionId}`) === "1",
  };
  const p = session.problem;

  $app.innerHTML = `<div class="session algo-session">
    <div class="session-bar">
      <a href="#/algo" class="ghost" title="Back to problems" style="color:var(--text-dim)">←</a>
      <span class="title">${esc(p.title)}</span>
      ${diffChip(p.difficulty)}
      <span class="mode-badge">${session.mode}</span>
      <span class="solved-badge ${st.solvedAt == null ? "hidden" : ""}" data-solved>✓ Solved</span>
      <span class="spacer"></span>
      <span class="timer" data-timer>--:--</span>
      <button data-pause class="${session.mode === "pausable" ? "" : "hidden"}">Pause</button>
      <button data-end class="danger">End session</button>
    </div>
    <div class="workspace" data-workspace>
      <section class="statement-pane" data-blur>
        <div class="scroll">
          <div class="statement">
            <div class="level-meta">#${p.number} · ${p.minutes}-minute session · implement <code>Solution.${esc(p.method)}</code></div>
            <h2>${esc(p.title)}</h2>
            <div class="md">${session.statement_html}</div>
          </div>
        </div>
      </section>
      <div class="gutter" data-gutter-x></div>
      <section class="code-pane" data-blur>
        <div class="editor-toolbar">
          <div class="file-tabs">
            <button class="file-tab active" data-file="solution">solution.py</button>
            <button class="file-tab" data-file="scratch" title="Your experiments, for Run scratch">scratch.py</button>
          </div>
          <span class="save-state" data-save-state></span>
          <button data-format title="Format with ruff (Shift+Alt+F)">Format</button>
          <button data-scratch title="Run scratch.py">Run scratch</button>
          <button data-run title="Run the examples (Ctrl+Enter)">▶ Run <kbd>Ctrl+↵</kbd></button>
          <button data-submit class="primary" title="Run the examples and the hidden tests (Ctrl+Shift+Enter)">Submit <kbd style="color:#dfe8ff;border-color:#9bb8ff">Ctrl+⇧+↵</kbd></button>
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
    if (el) el.textContent = st.dirty ? "Unsaved…" : st.lastSaved ? "Saved" : "";
  }
  async function save() {
    if (!st.dirty || st.timer.paused) return;
    const body = { code: solutionModel.getValue(), scratch: scratchModel.getValue() };
    st.dirty = false;
    try {
      const res = await api("PUT", `/api/algo/sessions/${sessionId}/code`, body);
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

  // ----- lint (when idle, and with every run)
  let lintTimer = null;
  function scheduleLint() {
    clearTimeout(lintTimer);
    lintTimer = setTimeout(runLint, 1500);
  }
  async function runLint() {
    if (st.timer.paused) return;
    try {
      setLint(await api("POST", `/api/algo/sessions/${sessionId}/lint`, { code: solutionModel.getValue() }));
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
      if (!st.timeUpShown) {
        st.timeUpShown = true;
        storage(`swe-prac-algo-timeup-${sessionId}`, "1");
        showTimeUp();
      }
    } else {
      if (remaining <= 120) el.classList.add("critical");
      else if (remaining <= 300) el.classList.add("low");
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
    try { syncTimer(await api("GET", `/api/algo/sessions/${sessionId}/timer`)); } catch { /* offline */ }
  }, 15000);

  async function showTimeUp() {
    const result = st.solvedAt != null
      ? `<p>Timed result: <strong>solved</strong> at ${fmtClock(st.solvedAt)}.</p>`
      : `<p>Timed result: <strong>not solved</strong> in ${fmtClock(st.timer.limit)} (locked).</p>
        <p>Keep going and a solve counts as overtime.</p>`;
    const choice = await modal({
      title: "⏰ Time's up",
      body: result,
      actions: [{ label: "Keep going (overtime)", value: "keep", kind: "ghost" }, { label: "End & review", value: "end", kind: "primary" }],
    });
    if (choice === "end") await endSession(false);
  }

  // ----- pausing hides the problem and the code
  function applyPaused() {
    const paused = st.timer.paused;
    $app.querySelectorAll("[data-blur]").forEach((el) => el.classList.toggle("blurred", paused));
    editor.updateOptions({ readOnly: paused });
    let overlay = q("[data-overlay]");
    if (paused && !overlay) {
      overlay = document.createElement("div");
      overlay.className = "overlay";
      overlay.dataset.overlay = "";
      overlay.innerHTML = `<div class="card"><h2>Paused</h2>
        <p>Your work is hidden while paused. This pause is recorded.</p>
        <button class="primary" data-resume>Resume</button></div>`;
      overlay.querySelector("[data-resume]").onclick = togglePause;
      workspace.appendChild(overlay);
    } else if (!paused && overlay) {
      overlay.remove();
    }
    setBusy(st.busy);
  }
  async function togglePause() {
    try {
      if (!st.timer.paused) await save();
      syncTimer(await api("POST", `/api/algo/sessions/${sessionId}/${st.timer.paused ? "resume" : "pause"}`));
      applyPaused();
    } catch (err) { toast(err.message, "bad"); }
  }

  // ----- files
  const models = { solution: solutionModel, scratch: scratchModel };
  function switchFile(name) {
    st.file = name;
    editor.setModel(models[name]);
    $app.querySelectorAll("[data-file]").forEach((b) => b.classList.toggle("active", b.dataset.file === name));
  }
  $app.querySelectorAll("[data-file]").forEach((b) => { b.onclick = () => switchFile(b.dataset.file); });

  // ----- results
  function renderResultTabs() {
    const r = st.lastResult;
    let testBadge = "";
    if (r) {
      const c = r.counts;
      testBadge = `<span class="badge ${r.all_passed ? "good" : "bad"}">${c.shown_passed + c.hidden_passed}/${c.shown_total + c.hidden_total}</span>`;
    }
    const lintCount = st.lint.issues.length;
    const tabs = [
      ["tests", `Tests ${testBadge}`],
      ["lint", `Lint <span class="badge ${lintCount ? "warnb" : ""}">${lintCount}</span>`],
      ["scratch", "Scratch output"],
    ];
    q("[data-result-tabs]").innerHTML = tabs.map(([key, label]) =>
      `<button class="tab ${st.resultsTab === key ? "active" : ""}" data-rtab="${key}">${label}</button>`).join("");
    q("[data-result-tabs]").querySelectorAll("[data-rtab]").forEach((b) => {
      b.onclick = () => { st.resultsTab = b.dataset.rtab; renderResultTabs(); renderResults(); };
    });
  }

  function renderResults() {
    const el = q("[data-results]");
    if (st.resultsTab === "lint") { el.innerHTML = renderLint(); bindLint(el); return; }
    if (st.busy) { el.innerHTML = `<div class="empty">${esc(st.busyText)}</div>`; return; }
    if (st.resultsTab === "scratch") { el.innerHTML = renderScratch(); return; }
    el.innerHTML = st.lastResult ? renderTestResult(st.lastResult) : renderExamples();
  }

  function renderExamples() {
    const intro = "<kbd>Ctrl+↵</kbd> <strong>Run</strong> checks these examples in full. <kbd>Ctrl+⇧+↵</kbd> <strong>Submit</strong> adds the hidden tests (counts only); pass them all to solve it.";
    const rows = session.examples.map((e) => `<tr><td>${esc(e.name)}</td>
      <td class="call">${esc(argsText(session.params, e.args))}</td><td>${esc(py(e.expect))}</td></tr>`).join("");
    return `<p class="faint" style="margin:0 0 10px">${intro}</p>
      <table class="steps"><tr><th>Example</th><th>Input</th><th>Expected</th></tr>${rows}</table>`;
  }

  function renderTestResult(r) {
    const c = r.counts;
    const parts = [];
    parts.push(`<div class="summary-row">
      <strong>${r.kind === "submit" ? "Submit (examples + hidden tests)" : "Run (examples)"}</strong>
      <span class="chip ${r.all_passed ? "good" : "bad"}">${c.shown_passed + c.hidden_passed}/${c.shown_total + c.hidden_total} passed</span>
      <span class="faint">${r.ms} ms</span></div>`);
    if (r.solved) {
      parts.push(`<div class="callout good"><strong>Solved at ${fmtClock(r.solved_at)}.</strong> Every test passes.
        End the session for the explained solution.</div>`);
    } else if (r.kind === "submit" && r.all_passed) {
      parts.push('<div class="callout good"><strong>All tests pass.</strong></div>');
    } else if (r.kind === "run" && r.all_passed) {
      parts.push('<div class="callout info">All examples pass. <strong>Submit</strong> to run the hidden tests.</div>');
    }
    if (r.import_error) {
      parts.push(`<div class="callout bad"><strong>Your code failed to load</strong><pre>${esc(r.import_error)}</pre>
        ${r.import_stdout ? `<div class="block-label">Output</div><pre>${esc(r.import_stdout)}</pre>` : ""}</div>`);
    }
    if (r.crashed) parts.push(`<div class="callout bad"><strong>Test process crashed</strong><pre>${esc(r.crashed)}</pre></div>`);
    if (r.timed_out) parts.push('<div class="callout bad"><strong>Timed out.</strong> Unfinished tests count as failed.</div>');
    if (r.stopped) {
      const why = r.stopped.replace(/^Too slow:\s*/, "");
      parts.push(`<div class="callout bad"><strong>Too slow.</strong> A hidden test ${esc(why)} The tests after it didn't run.</div>`);
    }
    const hidden = r.kind === "submit"
      ? `<td class="${c.hidden_passed === c.hidden_total ? "pass" : "fail"}">${c.hidden_passed}/${c.hidden_total}${c.too_slow ? ` <span class="warn">(${c.too_slow} too slow)</span>` : ""}</td>`
      : '<td class="faint">submit to run</td>';
    parts.push(`<table class="level-results"><tr><th>Examples</th><th>Hidden tests</th></tr>
      <tr><td class="${c.shown_passed === c.shown_total ? "pass" : "fail"}">${c.shown_passed}/${c.shown_total}</td>${hidden}</tr></table>`);
    for (const t of r.shown) {
      const ex = examples[t.id];
      parts.push(`<details class="test" ${t.passed ? "" : "open"}>
        <summary>${t.passed ? '<span class="pass">✓</span>' : '<span class="fail">✗</span>'}
          <span class="test-name">${esc(t.name)}</span>
          <span class="faint mono" style="font-size:12px">${t.ms != null ? `${t.ms} ms` : ""}</span></summary>
        <div class="body">
          ${t.error ? `<div class="callout bad"><pre>${esc(t.error)}</pre></div>` : ""}
          <table class="steps">
            <tr><th>Input</th><td class="call">${esc(argsText(session.params, ex?.args ?? []))}</td></tr>
            <tr><th>Expected</th><td>${esc(py(ex?.expect))}</td></tr>
            <tr class="${t.passed ? "" : "bad"}"><th>Got</th><td>${t.ran ? esc(t.actual ?? "") : '<span class="faint">not run</span>'}</td></tr>
          </table>
          ${t.stdout ? `<div class="block-label">stdout</div><pre class="out">${esc(t.stdout)}</pre>` : ""}
        </div></details>`);
    }
    if (r.kind === "submit") {
      parts.push('<p class="faint" style="font-size:12px">Hidden tests show pass counts only.</p>');
    }
    return parts.join("");
  }

  function renderLint() {
    const { issues, error } = st.lint;
    if (error) return `<div class="callout bad"><pre>${esc(error)}</pre></div>`;
    if (!issues.length) return '<div class="empty">✓ No lint issues (ruff).</div>';
    return `<p class="faint" style="margin-top:0;font-size:12px">ruff · informational. Click an issue to jump to it.</p>
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
    if (!o) {
      return `<div class="empty"><code>scratch.py</code> calls your method on the first example.
        Add inputs and prints, then <strong>Run scratch</strong>.</div>`;
    }
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
    const off = busy || st.timer.paused;
    for (const sel of ["[data-run]", "[data-submit]", "[data-scratch]"]) q(sel).disabled = off;
    q("[data-format]").disabled = st.timer.paused;
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
      const r = await api("POST", `/api/algo/sessions/${sessionId}/${kind}`, {
        code: solutionModel.getValue(), scratch: scratchModel.getValue(),
      });
      st.dirty = false;
      st.lastSaved = Date.now();
      st.lastResult = r;
      syncTimer(r.timer);
      setLint(r.lint);
      if (r.solved) {
        st.solvedAt = r.solved_at;
        q("[data-solved]").classList.remove("hidden");
        toast("Solved: every test passes", "good");
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
      st.scratchOut = await api("POST", `/api/algo/sessions/${sessionId}/scratch`, {
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
      await api("POST", `/api/algo/sessions/${sessionId}/end`, body);
      st.dirty = false;
      location.hash = `#/algo/review/${sessionId}`;
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

  // ----- resizable panes (the same remembered sizes as the coding session)
  const savedBottom = storage("swe-prac-bottom-height");
  if (savedBottom) q(".code-pane").style.setProperty("--bottom-height", savedBottom);
  resizableSplit(workspace, q("[data-gutter-x]"));
  dragGutter(q("[data-gutter-y]"), (e) => {
    const pane = q(".code-pane").getBoundingClientRect();
    const px = Math.min(pane.height - 120, Math.max(80, pane.bottom - e.clientY));
    q(".code-pane").style.setProperty("--bottom-height", `${px}px`);
    storage("swe-prac-bottom-height", `${px}px`);
  });

  // ----- first paint
  renderResultTabs();
  renderResults();
  renderTimer();
  applyPaused();
  runLint();
  if (!st.timer.paused) editor.focus();

  return async () => {
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
  };
}

// ---------------------------------------------------------------- review
export async function renderAlgoReview(sessionId) {
  let data;
  try {
    data = await api("GET", `/api/algo/sessions/${sessionId}/review`);
  } catch (err) {
    if (err.status === 409) { location.hash = `#/algo/session/${sessionId}`; return undefined; }
    throw err;
  }
  const r = data.results;
  const p = data.problem;
  const best = (b) => (b ? `best submit ${b.passed}/${b.total} tests${b.too_slow ? ` · ${b.too_slow} too slow` : ""}` : "no submit");
  const timedSub = r.timed.solved ? `at ${fmtClock(r.solved_at)} of ${fmtClock(r.time_limit)}` : best(r.timed.best);
  const finalValue = r.final.solved
    ? (r.timed.solved ? '<span class="pass">✓ Solved</span>' : '<span class="warn">✓ In overtime</span>')
    : "Not solved";
  const finalSub = r.final.solved ? `at ${fmtClock(r.solved_at)}` : best(r.final.best);

  $app.innerHTML = `${topnav("")}<main class="page">
    <p class="faint" style="margin:0 0 4px"><a href="#/history">← History</a> · <a href="#/algo/problem/${esc(p.id)}">Problem overview</a></p>
    <h1>${esc(p.title)}</h1>
    <p class="lead">${diffChip(p.difficulty)} <span class="faint">${data.mode === "strict" ? "Strict" : "Pausable"} session · ${fmtDate(data.started_at)} ·
      ${p.patterns.map(esc).join(", ")}</span></p>
    <div class="stat-grid">
      <div class="stat"><div class="label">Timed result</div>
        <div class="value">${r.timed.solved ? '<span class="pass">✓ Solved</span>' : "Not solved"}</div>
        <div class="sub">${timedSub}</div></div>
      <div class="stat"><div class="label">Including overtime</div>
        <div class="value">${finalValue}</div><div class="sub">${finalSub}</div></div>
      <div class="stat"><div class="label">Time used</div>
        <div class="value">${fmtClock(Math.min(r.elapsed, r.time_limit))}</div>
        <div class="sub">${r.overtime_seconds > 0 ? `+ ${fmtClock(r.overtime_seconds)} overtime` : `of ${fmtClock(r.time_limit)}`}</div></div>
      <div class="stat"><div class="label">Pauses</div>
        <div class="value">${r.pauses.count}</div>
        <div class="sub">${r.pauses.count ? `${fmtClock(r.pauses.total_seconds)} paused` : data.mode === "strict" ? "strict mode" : "none taken"} · ${plural(r.runs, "run")} · ${plural(r.submits, "submit")}</div></div>
    </div>
    ${foundationChips(data.foundations, "Study next")}
    <div class="review-tabs">
      <div class="tabs" data-review-tabs></div>
      <div data-review-panel></div>
    </div>
  </main>`;

  const tabs = [
    ["explanation", "Explanation"],
    ["hints", "Hints"],
    ["yours", "Your code"],
    ["statement", "Problem"],
    ["timeline", "Timeline"],
  ];
  let current = "explanation";
  let viewer = null;
  const panel = $app.querySelector("[data-review-panel]");

  async function show(key) {
    current = key;
    if (viewer) { viewer.dispose(); viewer = null; }
    $app.querySelector("[data-review-tabs]").innerHTML = tabs.map(([k, label]) =>
      `<button class="tab ${k === current ? "active" : ""}" data-k="${k}">${label}</button>`).join("");
    $app.querySelectorAll("[data-k]").forEach((b) => { b.onclick = () => show(b.dataset.k); });
    if (key === "yours") {
      panel.className = "review-panel code";
      panel.innerHTML = "";
      const monaco = await window.monacoReady;
      if (current !== key || !panel.isConnected) return;
      viewer = monaco.editor.create(panel, {
        value: data.code,
        language: "python", theme: "vs-dark", readOnly: true, domReadOnly: true, automaticLayout: true,
        minimap: { enabled: false }, fontSize: 13, scrollBeyondLastLine: false,
      });
      return;
    }
    panel.className = "review-panel md algo-study";
    if (key === "explanation") panel.innerHTML = data.explanation_html;
    else if (key === "hints") panel.innerHTML = data.hints_html;
    else if (key === "statement") panel.innerHTML = data.statement_html;
    else panel.innerHTML = renderTimeline(data);
  }
  show(current);
  return async () => { if (viewer) viewer.dispose(); };
}

function renderTimeline(data) {
  const events = data.submissions.map((s) => ({
    t: s.elapsed,
    html: `<td>${s.kind === "submit" ? "<strong>Submit</strong>" : "Run"}</td>
      <td>examples ${s.shown_passed}/${s.shown_total}${s.kind === "submit" ? `, hidden ${s.hidden_passed}/${s.hidden_total}${s.too_slow ? ` <span class="warn">(${s.too_slow} too slow)</span>` : ""}` : ""}</td>
      <td class="${s.all_passed ? "pass" : "fail"}">${s.all_passed ? "all passed" : "failing"}</td><td>${s.lint_count} lint</td>`,
  }));
  for (const pause of data.pauses) {
    const dur = (pause.ended_at ?? pause.started_at) - pause.started_at;
    events.push({ t: pause.start_elapsed, html: `<td class="warn">Pause</td><td>${fmtClock(dur)}</td><td></td><td></td>` });
  }
  const solvedAt = data.results.solved_at;
  if (solvedAt != null) {
    const over = solvedAt > data.results.time_limit ? '<span class="warn">overtime</span>' : "";
    events.push({ t: solvedAt + 0.001, html: `<td class="pass"><strong>Solved</strong></td><td></td><td>${over}</td><td></td>` });
  }
  events.sort((a, b) => a.t - b.t);
  if (!events.length) return '<p class="dim">No runs or submits in this session.</p>';
  return `<table class="table"><tr><th>At</th><th>Event</th><th>Detail</th><th>Result</th><th>Lint</th></tr>
    ${events.map((e) => `<tr><td class="mono">${fmtClock(e.t)}</td>${e.html}</tr>`).join("")}</table>`;
}

// ---------------------------------------------------------------- history (a section of the History page)
function historyTable(sessions, withProblem = true) {
  const rows = sessions.map((s) => {
    const href = s.status === "active" ? `#/algo/session/${s.id}` : `#/algo/review/${s.id}`;
    const over = s.elapsed > s.time_limit ? ` <span class="warn">+${fmtClock(s.elapsed - s.time_limit)}</span>` : "";
    const active = s.status === "active";
    return `<tr class="clickable" data-href="${href}">
      <td>${fmtDate(s.started_at)}</td>
      ${withProblem ? `<td>${esc(s.problem_title)}</td><td>${s.difficulty ? diffChip(s.difficulty) : ""}</td>` : ""}
      <td>${s.mode}</td>
      <td>${active ? '<span class="chip">in progress</span>' : resultLabel(s.timed)}${s.timed.solved ? ` <span class="faint">${fmtClock(s.solved_at)}</span>` : ""}</td>
      <td>${active ? "—" : s.final.solved && !s.timed.solved ? '<span class="warn">✓ in overtime</span>' : resultLabel(s.final)}</td>
      <td>${fmtClock(Math.min(s.elapsed, s.time_limit))}${over}</td>
      <td>${s.pauses.count ? `${s.pauses.count} (${fmtClock(s.pauses.total_seconds)})` : "—"}</td>
    </tr>`;
  }).join("");
  return `<table class="table"><tr><th>Date</th>${withProblem ? "<th>Problem</th><th>Difficulty</th>" : ""}<th>Mode</th><th>Timed result</th><th>Incl. overtime</th><th>Time</th><th>Pauses</th></tr>${rows}</table>`;
}

function bindRows() {
  $app.querySelectorAll("tr[data-href]").forEach((tr) => {
    tr.onclick = () => { location.hash = tr.dataset.href; };
  });
}

export async function algoHistoryTable() {
  const { sessions } = await api("GET", "/api/algo/history");
  if (!sessions.length) return '<p class="dim">No algorithm attempts yet. <a href="#/algo">Start one</a>.</p>';
  return historyTable(sessions);
}
