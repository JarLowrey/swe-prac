// System design practice: the question list, the 45-minute session (notes for each framework
// step plus a diagram), the review (pacing, your work beside the reference design, a self-check),
// the study pages and the framework guide. Every page returns its cleanup, if it needs one.

import {
  $app, api, esc, fmtClock, fmtDelta, plural, fmtDate, storage, toast, modal, chooseMode,
  confirmSpoil, topnav, resizableSplit,
} from "./common.js";
import { createDiagramEditor, renderDiagramSvg } from "./diagram.js";
import { foundationsSection } from "./learn.js";

const MINUTES = 45;
const timerLabel = (t) => (t.paused ? "paused" : t.overtime ? "overtime" : `${fmtClock(t.remaining)} left`);
const scoreText = (score) => (score ? `${score.done}/${score.total}` : "not reviewed");

function confirmEnd() {
  return modal({
    title: "End this session?",
    body: "<p>Your notes and diagram are locked. The reference design and the self-review checklist open on the review page.</p>",
    actions: [{ label: "Keep working", value: false, kind: "ghost" }, { label: "End & review", value: true, kind: "primary" }],
  });
}

// ---------------------------------------------------------------- home page card
export async function designTrackCard() {
  const [{ questions, time_limit: limit }, { session: active }] = await Promise.all([
    api("GET", "/api/design/questions"), api("GET", "/api/design/active"),
  ]);
  const attempts = questions.reduce((sum, q) => sum + q.attempts, 0);
  const status = active
    ? `<span class="chip good">In progress: ${esc(active.question.title)} · ${timerLabel(active.timer)}</span>`
    : `<span class="faint">${attempts ? `${plural(attempts, "attempt")} so far` : "No attempts yet"}</span>`;
  return `<a class="track-card" href="#/design">
    <div class="track-head"><span class="track-mark design">◇</span><h2>System design</h2></div>
    <p>45 minutes, one open-ended question, worked through seven steps: requirements, estimates,
      API, data model, high-level design, deep dives and wrap-up. You write notes and draw a diagram,
      then compare with a reference design and score yourself.</p>
    <ul class="track-facts"><li>${plural(questions.length, "question")}</li><li>${limit / 60} min</li><li>self-reviewed</li></ul>
    <div class="track-foot">${status}<span class="track-cta">Open →</span></div>
  </a>`;
}

// ---------------------------------------------------------------- question list
export async function renderDesignHome() {
  const [{ questions, steps }, { session: active }, foundations] = await Promise.all([
    api("GET", "/api/design/questions"), api("GET", "/api/design/active"),
    foundationsSection("design", "The concepts every question builds on: networking and APIs, data, the building blocks, and reliability. Each question's hints link to the sections it needs."),
  ]);
  const preferUnseen = storage("swe-prac-design-prefer-unseen") !== "0";

  const banner = active ? `<div class="banner">
      <div><strong>Session in progress:</strong> ${esc(active.question.title)} · ${active.mode} ·
        Step ${active.current_step} · <span class="mono">${timerLabel(active.timer)}</span></div>
      <div style="display:flex;gap:8px"><button class="primary" data-resume>Resume</button>
        <button class="danger" data-end-active>End session</button></div>
    </div>` : "";

  let elapsed = 0;
  const strip = steps.map((s) => {
    elapsed += s.minutes;
    return `<li title="${esc(s.output)}"><span class="n">${s.step}</span>${esc(s.title)}<span class="faint">${s.minutes}m · by ${elapsed}:00</span></li>`;
  }).join("");

  const cards = questions.map((q) => {
    const inSession = active && active.question.id === q.id;
    const lock = inSession ? 'disabled title="Locked while this question is in a running session"' : "";
    return `<article class="problem-card">
      <span class="num">QUESTION ${q.number}</span>
      <h3>${esc(q.title)}</h3>
      <p>${esc(q.prompt)}</p>
      <div class="study-links">
        <button class="small" data-study="hints" data-qid="${esc(q.id)}" ${lock}>Hints</button>
        <button class="small" data-study="reference" data-qid="${esc(q.id)}" ${lock}>Reference design</button>
      </div>
      <div class="meta">
        <span class="dim" style="font-size:12px">${q.attempts ? `${plural(q.attempts, "attempt")} · best ${scoreText(q.best)}` : "Not attempted"}</span>
        <button class="primary small" data-start="${esc(q.id)}" ${active ? "disabled" : ""}>Start</button>
      </div>
    </article>`;
  }).join("");

  $app.innerHTML = `${topnav("design")}<main class="page">
    <h1>System design practice</h1>
    <p class="lead">One open-ended question, ${MINUTES} minutes. The prompt is deliberately vague: you
      set the requirements, size it, sketch the API and data model, draw the design and go deep on the
      hardest parts. Afterwards you compare with a reference design and tick off what you covered.</p>
    ${banner}
    ${foundations}
    <h2 class="section-title">The seven steps</h2>
    <ol class="step-strip">${strip}</ol>
    <p class="faint" style="margin:8px 0 0"><a href="#/design/framework">Read the framework guide →</a>
      what each step should produce, what interviewers grade, common mistakes.</p>
    <h2 class="section-title">Questions</h2>
    <div class="random-row">
      <button data-random ${active ? "disabled" : ""}>🎲 Start a random question</button>
      <label><input type="checkbox" data-unseen ${preferUnseen ? "checked" : ""}> Prefer questions I haven't tried</label>
    </div>
    <div class="problem-grid">${cards || '<p class="dim">No questions found in <code>designs/</code>.</p>'}</div>
  </main>`;

  const unseenBox = $app.querySelector("[data-unseen]");
  unseenBox.addEventListener("change", () => storage("swe-prac-design-prefer-unseen", unseenBox.checked ? "1" : "0"));

  const start = async (questionId) => {
    const mode = await chooseMode(MINUTES, "the question and the seven steps");
    if (!mode) return;
    try {
      const s = await api("POST", "/api/design/sessions", { question_id: questionId, mode, prefer_unseen: unseenBox.checked });
      location.hash = `#/design/session/${s.id}`;
    } catch (err) { toast(err.message, "bad"); }
  };
  $app.querySelectorAll("[data-start]").forEach((b) => b.addEventListener("click", () => start(b.dataset.start)));
  $app.querySelector("[data-random]").addEventListener("click", () => start(null));
  $app.querySelectorAll("[data-study]").forEach((b) => b.addEventListener("click", async () => {
    const q = questions.find((x) => x.id === b.dataset.qid);
    if (!q.attempts && !(await confirmSpoil(q.title, "hints or reference design"))) return;
    location.hash = `#/design/question/${q.id}/${b.dataset.study}`;
  }));
  $app.querySelector("[data-resume]")?.addEventListener("click", () => { location.hash = `#/design/session/${active.id}`; });
  $app.querySelector("[data-end-active]")?.addEventListener("click", async () => {
    if (!(await confirmEnd())) return;
    await api("POST", `/api/design/sessions/${active.id}/end`);
    location.hash = `#/design/review/${active.id}`;
  });
}

// ---------------------------------------------------------------- session
export async function renderDesignSession(sessionId) {
  let session;
  try {
    session = await api("GET", `/api/design/sessions/${sessionId}`);
  } catch (err) {
    if (err.status === 410) { location.hash = `#/design/review/${sessionId}`; return undefined; }
    throw err;
  }
  const monaco = await window.monacoReady;
  const steps = session.steps;
  const last = steps[steps.length - 1].step;
  const st = {
    s: session,
    timer: { ...session.timer, syncedAt: performance.now() },
    tab: String(session.current_step),
    dirty: false,
    lastSaved: null,
    timeUpShown: storage(`swe-prac-design-timeup-${sessionId}`) === "1",
  };

  $app.innerHTML = `<div class="session design-session">
    <div class="session-bar">
      <a href="#/design" class="ghost" title="Back to questions" style="color:var(--text-dim)">←</a>
      <span class="title">${esc(session.question.title)}</span>
      <span class="level-pills" data-pills></span>
      <span class="mode-badge">${session.mode}</span>
      <span class="spacer"></span>
      <span class="pace" data-pace></span>
      <span class="timer" data-timer>--:--</span>
      <button data-pause class="${session.mode === "pausable" ? "" : "hidden"}">Pause</button>
      <button data-next class="primary"></button>
      <button data-end class="danger">End session</button>
    </div>
    <div class="workspace" data-workspace>
      <section class="statement-pane" data-blur>
        <div class="scroll">
          <div class="prompt-card">
            <span class="num">QUESTION ${session.question.number}</span>
            <h2>${esc(session.question.title)}</h2>
            <p>${esc(session.question.prompt)}</p>
          </div>
          <ol class="step-list" data-steps></ol>
        </div>
      </section>
      <div class="gutter" data-gutter-x></div>
      <section class="notes-pane" data-blur>
        <div class="editor-toolbar">
          <div class="file-tabs" data-tabs></div>
          <span class="save-state" data-save-state></span>
        </div>
        <div class="notes-body">
          <div class="editor-host" data-editor-host></div>
          <div class="diagram-host hidden" data-diagram-host></div>
        </div>
      </section>
    </div>
  </div>`;
  const q = (sel) => $app.querySelector(sel);
  const workspace = q("[data-workspace]");

  // ----- editors: one plain-text model per step, plus the diagram
  const models = Object.fromEntries(steps.map((x) => [String(x.step), monaco.editor.createModel(session.notes[x.step] ?? "", "plaintext")]));
  const editor = monaco.editor.create(q("[data-editor-host]"), {
    model: models[st.tab],
    theme: "vs-dark",
    fontSize: 14,
    fontFamily: "'Cascadia Code', 'JetBrains Mono', Consolas, monospace",
    wordWrap: "on",
    lineNumbers: "off",
    glyphMargin: false,
    folding: false,
    minimap: { enabled: false },
    automaticLayout: true,
    scrollBeyondLastLine: false,
    renderLineHighlight: "none",
    padding: { top: 12 },
    tabSize: 2,
    fixedOverflowWidgets: true,
    // While readOnly is set, also mark the hidden textarea readonly so mobile keeps its keyboard closed.
    domReadOnly: true,
  });
  const markDirty = () => { st.dirty = true; renderSaveState(); };
  const subs = Object.values(models).map((m) => m.onDidChangeContent(markDirty));
  const diagram = createDiagramEditor(q("[data-diagram-host]"), session.diagram, { onChange: markDirty });
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => save());

  const work = () => ({
    notes: Object.fromEntries(Object.entries(models).map(([k, m]) => [k, m.getValue()])),
    diagram: diagram.getModel(),
  });

  // ----- saving
  function renderSaveState() {
    const el = q("[data-save-state]");
    if (el) el.textContent = st.dirty ? "Unsaved…" : st.lastSaved ? "Saved" : "";
  }
  async function save() {
    if (!st.dirty || st.timer.paused) return;
    st.dirty = false;
    try {
      const res = await api("PUT", `/api/design/sessions/${sessionId}/notes`, work());
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
      if (!st.timeUpShown) { st.timeUpShown = true; storage(`swe-prac-design-timeup-${sessionId}`, "1"); showTimeUp(); }
    } else {
      if (remaining <= 300) el.classList.add("critical");
      else if (remaining <= 600) el.classList.add("low");
      el.textContent = fmtClock(remaining);
    }
    el.title = `Elapsed ${fmtClock(elapsed)} of ${fmtClock(st.timer.limit)}`;
    const pauseBtn = q("[data-pause]");
    pauseBtn.textContent = st.timer.paused ? "Resume" : "Pause";
    pauseBtn.disabled = !st.timer.paused && remaining <= 0;
    renderPace(elapsed);
  }
  // Time on the current step against its target, in the bar and in the step list.
  function renderPace(elapsed) {
    const step = steps.find((x) => x.step === st.s.current_step);
    const spent = Math.max(0, elapsed - (st.s.step_starts[String(step.step)] ?? 0));
    const over = spent > step.minutes * 60;
    const text = `${fmtClock(spent)} / ${fmtClock(step.minutes * 60)}`;
    const pace = q("[data-pace]");
    pace.className = `pace${over ? " warn" : ""}`;
    pace.textContent = `${step.title} · ${text}${over ? " over" : ""}`;
    const clock = q("[data-step-clock]");
    if (clock) { clock.textContent = text; clock.classList.toggle("warn", over); }
  }
  const tick = setInterval(renderTimer, 250);
  const resync = setInterval(async () => {
    try { syncTimer(await api("GET", `/api/design/sessions/${sessionId}/timer`)); } catch { /* offline */ }
  }, 15000);

  async function showTimeUp() {
    const choice = await modal({
      title: "⏰ Time's up",
      body: `<p>In a real interview the conversation ends here. You reached step ${st.s.current_step} of ${steps.length}.</p>
        <p>You can keep going untimed; steps you start from now on are marked as overtime.</p>`,
      actions: [{ label: "Keep going (overtime)", value: "keep", kind: "ghost" }, { label: "End & review", value: "end", kind: "primary" }],
    });
    if (choice === "end") await endSession(false);
  }

  // ----- steps (left pane, bar pills, the Next button)
  function renderSteps() {
    const cur = st.s.current_step;
    const starts = st.s.step_starts;
    let targetEnd = 0;
    q("[data-steps]").innerHTML = steps.map((x) => {
      targetEnd += x.minutes * 60;
      const started = starts[String(x.step)];
      const later = Object.entries(starts).filter(([k]) => Number(k) > x.step).map(([, v]) => v);
      const state = x.step === cur ? "current" : x.step < cur ? "done" : "upcoming";
      let meta = "";
      if (state === "current") {
        meta = `<div class="step-meta">On this step: <span class="mono" data-step-clock></span></div>`;
      } else if (state === "done") {
        meta = started == null ? '<div class="step-meta faint">Skipped</div>'
          : `<div class="step-meta">✓ ${fmtClock(Math.min(...later) - started)} (target ${fmtClock(x.minutes * 60)})</div>`;
      }
      return `<li class="step-item ${state}" data-open="${x.step}">
        <div class="step-head"><span class="step-num">${state === "done" ? "✓" : x.step}</span>
          <strong>${esc(x.title)}</strong><span class="step-time">${x.minutes} min · by ${fmtClock(targetEnd)}</span></div>
        <div class="step-output">${esc(x.output)}</div>
        ${state === "current" ? `<div class="step-guide">${esc(x.guide)}</div>` : ""}
        ${meta}
      </li>`;
    }).join("");
    q("[data-steps]").querySelectorAll("[data-open]").forEach((li) => {
      li.onclick = () => switchTab(li.dataset.open);
    });
    q("[data-pills]").innerHTML = steps.map((x) => {
      const cls = x.step < cur ? "done" : x.step === cur ? "current" : "";
      return `<span class="level-pill ${cls}" title="${esc(x.title)}">${esc(x.short)}</span>`;
    }).join("");
    const next = steps.find((x) => x.step === cur + 1);
    const nextBtn = q("[data-next]");
    nextBtn.classList.toggle("hidden", !next);
    if (next) {
      nextBtn.textContent = `Next: ${next.title} →`;
      nextBtn.title = `Start step ${next.step} (${next.minutes} min). You can still edit earlier notes.`;
    }
    q("[data-end]").className = cur === last ? "primary" : "danger";
    renderTabs();
    renderPace(currentElapsed());
  }

  function renderTabs() {
    const tabs = steps.map((x) => {
      const cur = x.step === st.s.current_step ? ' <span class="cur-dot" title="Current step"></span>' : "";
      return `<button class="file-tab ${st.tab === String(x.step) ? "active" : ""}" data-tab="${x.step}" title="${esc(x.output)}">${x.step}. ${esc(x.title)}${cur}</button>`;
    });
    tabs.push(`<button class="file-tab ${st.tab === "diagram" ? "active" : ""}" data-tab="diagram" title="Box-and-arrow diagram for the high-level design">◇ Diagram</button>`);
    q("[data-tabs]").innerHTML = tabs.join("");
    q("[data-tabs]").querySelectorAll("[data-tab]").forEach((b) => { b.onclick = () => switchTab(b.dataset.tab); });
  }

  function switchTab(tab) {
    st.tab = tab;
    const isDiagram = tab === "diagram";
    q("[data-editor-host]").classList.toggle("hidden", isDiagram);
    q("[data-diagram-host]").classList.toggle("hidden", !isDiagram);
    if (!isDiagram) {
      editor.setModel(models[tab]);
      if (!st.timer.paused) editor.focus();
    }
    renderTabs();
  }

  async function nextStep() {
    const step = st.s.current_step + 1;
    if (step > last || st.timer.paused) return;
    await save();
    try {
      const s = await api("POST", `/api/design/sessions/${sessionId}/step`, { step });
      st.s.current_step = s.current_step;
      st.s.step_starts = s.step_starts;
      syncTimer(s.timer);
      renderSteps();
      switchTab(String(step));
    } catch (err) { toast(err.message, "bad"); }
  }

  // ----- pausing
  function applyPaused() {
    const paused = st.timer.paused;
    $app.querySelectorAll("[data-blur]").forEach((el) => el.classList.toggle("blurred", paused));
    editor.updateOptions({ readOnly: paused });
    diagram.setReadOnly(paused);
    q("[data-next]").disabled = paused;
    let overlay = q("[data-overlay]");
    if (paused && !overlay) {
      overlay = document.createElement("div");
      overlay.className = "overlay";
      overlay.dataset.overlay = "";
      overlay.innerHTML = `<div class="card"><h2>Paused</h2>
        <p>The question and your notes are hidden while the clock is stopped. This pause is recorded.</p>
        <button class="primary" data-resume>Resume</button></div>`;
      overlay.querySelector("[data-resume]").onclick = togglePause;
      workspace.appendChild(overlay);
    } else if (!paused && overlay) {
      overlay.remove();
    }
  }
  async function togglePause() {
    try {
      if (!st.timer.paused) await save();
      syncTimer(await api("POST", `/api/design/sessions/${sessionId}/${st.timer.paused ? "resume" : "pause"}`));
      applyPaused();
    } catch (err) { toast(err.message, "bad"); }
  }

  async function endSession(ask = true) {
    if (ask && !(await confirmEnd())) return;
    try {
      await api("POST", `/api/design/sessions/${sessionId}/end`, st.timer.paused ? undefined : work());
      st.dirty = false;
      location.hash = `#/design/review/${sessionId}`;
    } catch (err) { toast(err.message, "bad"); }
  }

  q("[data-next]").onclick = nextStep;
  q("[data-pause]").onclick = togglePause;
  q("[data-end]").onclick = () => endSession(true);
  const keyHandler = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); }
  };
  window.addEventListener("keydown", keyHandler);
  resizableSplit(workspace, q("[data-gutter-x]"));

  renderSteps();
  switchTab(st.tab);
  renderTimer();
  applyPaused();

  return async () => {
    await save();
    clearInterval(autosave); clearInterval(tick); clearInterval(resync);
    window.removeEventListener("beforeunload", beforeUnload);
    window.removeEventListener("keydown", keyHandler);
    subs.forEach((s) => s.dispose());
    editor.dispose();
    Object.values(models).forEach((m) => m.dispose());
  };
}

// ---------------------------------------------------------------- review
// The foundations links are grouped by page, in the order the question lists them.
function hintsHtml(hints) {
  const byPage = new Map();
  for (const f of hints.foundations ?? []) {
    if (!byPage.has(f.page_title)) byPage.set(f.page_title, []);
    byPage.get(f.page_title).push(`<a class="chip link" href="${esc(f.href)}">${esc(f.title)}</a>`);
  }
  const groups = [...byPage].map(([page, chips]) => `<div class="foundation-group">
    <span class="faint">${esc(page)}</span> ${chips.join(" ")}</div>`).join("");
  return `<div class="callout info hint-box"><div><strong>The hard part:</strong> ${esc(hints.hard_part)}</div>
    <div><strong>Building blocks it tests:</strong> ${hints.building_blocks.map((b) => `<span class="chip">${esc(b)}</span>`).join(" ")}</div>
    ${groups ? `<div><strong>Foundations to review</strong> (the reference design links to them too)${groups}</div>` : ""}</div>`;
}

function notesHtml(steps, notes) {
  return steps.map((x) => {
    const text = (notes[x.step] ?? "").trim();
    return `<div class="notes-block"><h4>${x.step}. ${esc(x.title)}</h4>
      ${text ? `<pre>${esc(text)}</pre>` : '<p class="faint">(empty)</p>'}</div>`;
  }).join("");
}

export async function renderDesignReview(sessionId) {
  let data;
  try {
    data = await api("GET", `/api/design/sessions/${sessionId}/review`);
  } catch (err) {
    if (err.status === 409) { location.hash = `#/design/session/${sessionId}`; return undefined; }
    throw err;
  }
  const r = data.results;
  const pacingRows = r.steps.map((x) => {
    const status = x.started_at == null ? '<span class="faint">not reached</span>'
      : x.overtime ? '<span class="warn">overtime</span>'
      : x.delta <= 0 ? '<span class="pass">on time</span>' : '<span class="warn">over</span>';
    return `<tr><td>${x.step}. ${esc(x.title)}</td>
      <td>${fmtClock(x.target)}</td>
      <td>${x.started_at == null ? "—" : fmtClock(x.started_at)} <span class="faint">(${fmtClock(x.target_start)})</span></td>
      <td>${x.spent == null ? "—" : fmtClock(x.spent)}</td>
      <td>${fmtDelta(x.delta)}</td><td>${status}</td></tr>`;
  }).join("");
  const deep = r.steps.find((x) => x.title === "Deep dives");

  $app.innerHTML = `${topnav("")}<main class="page">
    <p class="faint" style="margin:0 0 4px"><a href="#/history">← History</a></p>
    <h1>${esc(data.question.title)}</h1>
    <p class="lead">${data.mode === "strict" ? "Strict" : "Pausable"} system design session · ${fmtDate(data.started_at)}</p>
    <div class="stat-grid">
      <div class="stat"><div class="label">Time used</div>
        <div class="value">${fmtClock(Math.min(r.elapsed, r.time_limit))}</div>
        <div class="sub">${r.overtime_seconds > 0 ? `+ ${fmtClock(r.overtime_seconds)} overtime` : `of ${fmtClock(r.time_limit)}`}</div></div>
      <div class="stat"><div class="label">Steps reached</div>
        <div class="value">${r.steps_reached}/${r.steps.length}</div>
        <div class="sub">${!deep ? "" : deep.started_at != null ? `Deep dives started at ${fmtClock(deep.started_at)}` : "Deep dives not reached"}</div></div>
      <div class="stat"><div class="label">Self-review</div>
        <div class="value" data-score>${scoreText(data.score)}</div>
        <div class="sub" data-score-sub></div></div>
      <div class="stat"><div class="label">Pauses</div>
        <div class="value">${r.pauses.count}</div>
        <div class="sub">${r.pauses.count ? `${fmtClock(r.pauses.total_seconds)} paused` : data.mode === "strict" ? "strict mode" : "none taken"}</div></div>
    </div>
    <h2 class="section-title">Pacing</h2>
    <table class="table"><tr><th>Step</th><th>Target</th><th>Started at (target)</th><th>Time on step</th><th>vs target</th><th></th></tr>${pacingRows}</table>
    <div class="review-tabs">
      <div class="tabs" data-review-tabs></div>
      <div class="review-panel" data-review-panel></div>
    </div>
  </main>`;

  let picked = data.assessment ?? { checklist: [], key_points: [] };
  const renderScore = (score) => {
    $app.querySelector("[data-score]").textContent = scoreText(score);
    $app.querySelector("[data-score-sub]").textContent = score
      ? `${score.key_points}/${data.key_points.length} key points · ${score.checklist}/${data.checklist.length} checklist`
      : "tick the Self-review tab";
  };
  renderScore(data.score);

  const checks = (items, group) => `<ul class="checks">${items.map((text, i) => `<li><label>
      <input type="checkbox" data-group="${group}" data-i="${i}" ${picked[group].includes(i) ? "checked" : ""}>
      <span>${esc(text)}</span></label></li>`).join("")}</ul>`;

  const tabs = [
    ["assess", "Self-review"],
    ["compare", "Your notes vs reference"],
    ["diagram", "Your diagram"],
    ["reference", "Reference design"],
  ];
  let current = "assess";
  const panel = $app.querySelector("[data-review-panel]");

  function show(key) {
    current = key;
    $app.querySelector("[data-review-tabs]").innerHTML = tabs.map(([k, label]) =>
      `<button class="tab ${k === current ? "active" : ""}" data-k="${k}">${label}</button>`).join("");
    $app.querySelectorAll("[data-k]").forEach((b) => { b.onclick = () => show(b.dataset.k); });
    panel.className = "review-panel";
    if (key === "assess") {
      panel.innerHTML = `<p class="dim" style="margin-top:0">There is no answer key for system design, so you grade yourself.
        Tick only what your notes and diagram actually show; read the reference design first if you're unsure.
        Your ticks save as you go.</p>
        <div class="assess-grid">
          <section><h3>Key points for this question</h3>${checks(data.key_points, "key_points")}</section>
          <section><h3>Framework checklist</h3>${checks(data.checklist, "checklist")}</section>
        </div>`;
      panel.querySelectorAll("input[type=checkbox]").forEach((box) => {
        box.onchange = async () => {
          const group = box.dataset.group, i = Number(box.dataset.i);
          const set = new Set(picked[group]);
          if (box.checked) set.add(i); else set.delete(i);
          const next = { ...picked, [group]: [...set] };
          try {
            const res = await api("PUT", `/api/design/sessions/${sessionId}/assessment`, next);
            picked = res.assessment;
            renderScore(res.score);
          } catch (err) { box.checked = !box.checked; toast(err.message, "bad"); }
        };
      });
    } else if (key === "compare") {
      panel.innerHTML = `<div class="compare">
        <section><h3>Your notes</h3>${notesHtml(data.steps, data.notes)}</section>
        <section class="md"><h3>Reference design</h3>${data.reference_html}</section></div>`;
    } else if (key === "diagram") {
      const svg = renderDiagramSvg(data.diagram);
      panel.innerHTML = svg ? `<div class="diagram-view">${svg}</div>` : '<p class="dim">You didn\'t draw a diagram in this session.</p>';
    } else {
      panel.className = "review-panel md";
      panel.innerHTML = hintsHtml(data.hints) + data.reference_html;
    }
  }
  show(current);
  return undefined;
}

// ---------------------------------------------------------------- study page
export async function renderDesignStudy(questionId, kind) {
  const data = await api("GET", `/api/design/questions/${encodeURIComponent(questionId)}/${kind}`);
  const tabs = [["hints", "Hints"], ["reference", "Reference design"]];
  $app.innerHTML = `${topnav("design")}<main class="page">
    <p class="faint" style="margin:0 0 4px"><a href="#/design">← System design</a></p>
    <h1>${esc(data.question.title)}</h1>
    <p class="lead">${esc(data.question.prompt)}</p>
    <div class="review-tabs" style="margin-top:0">
      <div class="tabs">${tabs.map(([k, label]) =>
        `<a class="tab ${k === kind ? "active" : ""}" href="#/design/question/${esc(questionId)}/${k}">${label}</a>`).join("")}</div>
      <div class="review-panel md">${kind === "hints"
        ? `${hintsHtml(data.hints)}<p class="dim">The prompt is deliberately open. In the interview you'd set the
            scope yourself, so these only say where the difficulty is, not how to solve it.</p>`
        : `${data.reference_html}<h3>What a strong answer covers</h3>
            <ul>${data.key_points.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>`}</div>
    </div>
  </main>`;
  return undefined;
}

// ---------------------------------------------------------------- framework guide
export async function renderFramework() {
  const fw = await api("GET", "/api/design/framework");
  $app.innerHTML = `${topnav("design")}<main class="page guide">
    <p class="faint" style="margin:0 0 4px"><a href="#/design">← System design</a></p>
    <h1>The ${fw.time_limit / 60}-minute framework</h1>
    <div class="md">${fw.guide_html}</div>
    <h2 class="section-title">One-page checklist</h2>
    <p class="dim">The same list you tick on each review page.</p>
    <ul class="checks static">${fw.checklist.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>
    ${fw.walkthrough_html ? `<details class="walkthrough"><summary>Worked walkthrough: a vacation-rental booking system
      <span class="faint">(spoils the booking question)</span></summary><div class="md">${fw.walkthrough_html}</div></details>` : ""}
  </main>`;
  return undefined;
}

// ---------------------------------------------------------------- history (a section of the History page)
export async function designHistoryTable() {
  const { sessions } = await api("GET", "/api/design/history");
  if (!sessions.length) return '<p class="dim">No system design attempts yet. <a href="#/design">Start one</a>.</p>';
  const rows = sessions.map((s) => {
    const href = s.status === "active" ? `#/design/session/${s.id}` : `#/design/review/${s.id}`;
    const over = s.elapsed > s.time_limit ? ` <span class="warn">+${fmtClock(s.elapsed - s.time_limit)}</span>` : "";
    return `<tr class="clickable" data-href="${href}">
      <td>${fmtDate(s.started_at)}</td>
      <td>${esc(s.question_title)}</td>
      <td>${s.mode}</td>
      <td>${s.status === "active" ? '<span class="chip">in progress</span>' : `${s.steps_reached}/${s.step_count}`}</td>
      <td>${s.status === "active" ? "—" : scoreText(s.score)}</td>
      <td>${fmtClock(Math.min(s.elapsed, s.time_limit))}${over}</td>
      <td>${s.pauses.count ? `${s.pauses.count} (${fmtClock(s.pauses.total_seconds)})` : "—"}</td>
    </tr>`;
  }).join("");
  return `<table class="table"><tr><th>Date</th><th>Question</th><th>Mode</th><th>Steps reached</th><th>Self-review</th><th>Time</th><th>Pauses</th></tr>${rows}</table>`;
}
