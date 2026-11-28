// System design practice: the question list, the 45-minute session (one whiteboard, an AI
// interviewer to ask for hints, sound recording; the round isn't split into steps), the review
// (your board, the hints you asked for, your recordings, the reference design, a self-check), the
// study pages and the framework guide. Every page returns its cleanup, if it needs one.

import {
  $app, api, esc, fmtClock, plural, fmtDate, storage, toast, modal, chooseMode,
  confirmSpoil, topnav, resizableSplit,
} from "./common.js";
import { createWhiteboard, renderBoardSvg } from "./whiteboard.js";
import {
  PERSONAS, PROVIDERS, aiSettings, askApi, modelName, pastePrompt, saveAiSettings, systemPrompt, userPrompt, verdict,
} from "./interviewer.js";
import {
  clipBlob, clipExtension, createRecorder, deleteClip, listClips, recordingSupported,
} from "./recorder.js";
import { DEFAULT_SPEECH, MODELS, createTranscriber, modelSaved, transcriptionSupported } from "./transcribe.js";
import { foundationsSection } from "./learn.js";

const MINUTES = 45;
const timerLabel = (t) => (t.paused ? "paused" : t.overtime ? "overtime" : `${fmtClock(t.remaining)} left`);
const scoreText = (score) => (score ? `${score.done}/${score.total}` : "not reviewed");

// Which speech model transcribes the recording about to start: a key of MODELS, or null to not
// record after all. The last choice is preselected, and a model already in this browser says so.
async function chooseSpeech() {
  const last = MODELS[storage("swe-prac-design-speech")] ? storage("swe-prac-design-speech") : DEFAULT_SPEECH;
  const { fast, accurate } = MODELS;
  const [fastSaved, accurateSaved] = await Promise.all([modelSaved(fast), modelSaved(accurate)]);
  const about = (m, saved) => `${m.label}, ${m.params}M parameters, ${m.mb} MB ${saved ? "(already downloaded)" : "download"}`;
  const pending = modal({
    title: "Transcribe with which model?",
    body: `<p>Your recording is transcribed in this browser as you talk, for the AI interviewer. The
        model loads when you pick it, and downloads only the first time.</p>
      <ul class="mode-help">
        <li><strong>${fast.name}</strong> &mdash; ${about(fast, fastSaved)}. About twice as fast; mishears more words.</li>
        <li><strong>${accurate.name}</strong> &mdash; ${about(accurate, accurateSaved)}. Better with technical terms.</li>
      </ul>`,
    actions: [
      { label: "Cancel", value: null, kind: "ghost" },
      { label: fast.name, value: "fast", kind: last === "fast" ? "primary" : "" },
      { label: accurate.name, value: "accurate", kind: last === "accurate" ? "primary" : "" },
    ],
  });
  [...document.querySelectorAll(".modal-backdrop")].pop()?.querySelector(".actions .primary")?.focus();
  const choice = await pending;
  if (choice) storage("swe-prac-design-speech", choice);
  return choice;
}

function confirmEnd() {
  return modal({
    title: "End this session?",
    body: "<p>Your board locks, and the reference design and self-review unlock.</p>",
    actions: [{ label: "Keep working", value: false, kind: "ghost" }, { label: "End & review", value: true, kind: "primary" }],
  });
}

// ---------------------------------------------------------------- AI settings
const aiStatus = () => {
  const s = aiSettings();
  return s.key
    ? `Using your ${PROVIDERS[s.provider].name} key (${modelName(s.provider, s.model)})`
    : "No API key: Ask copies a prompt for your own AI agent";
};

// Pick Claude, Gemini or ChatGPT, then that service's key and model. Each service keeps its own
// key, so switching back and forth loses nothing. Resolves to true when the settings changed.
async function openAiSettings() {
  const first = aiSettings();
  const drafts = {}; // provider -> {key, model, remember} as edited in this dialog
  const pending = modal({
    title: "AI interviewer",
    body: `<p>Hints come from the AI service you pick, with your own API key. Keys stay in this browser
        and go only to that service.</p>
      <div class="ai-form">
        <fieldset class="lang-picker"><legend>Service</legend>
          ${Object.entries(PROVIDERS).map(([id, p]) => `<label><input type="radio" name="ai-provider" value="${id}" ${id === first.provider ? "checked" : ""}> ${p.name}</label>`).join("")}
        </fieldset>
        <label class="field"><span data-key-label></span>
          <input type="password" data-key autocomplete="off" spellcheck="false" placeholder="Paste your key"></label>
        <label class="field"><span>Model</span>
          <input data-model list="ai-models" autocomplete="off" spellcheck="false"><datalist id="ai-models"></datalist></label>
        <label class="check"><input type="checkbox" data-remember> Remember the key in this browser</label>
        <p class="faint" style="margin:0"><a data-key-link target="_blank" rel="noopener"></a> · Pick a model or type any model ID.</p>
      </div>
      <p class="faint">No key? Ask copies a prompt to paste into any AI agent, and you paste the reply back.</p>`,
    actions: [
      { label: "Remove key", value: "remove", kind: "ghost danger" },
      { label: "Cancel", value: null, kind: "ghost" },
      { label: "Save", value: "save", kind: "primary" },
    ],
    read: (dialog, value) => {
      if (!value) return null;
      const provider = dialog.querySelector('[name="ai-provider"]:checked').value;
      keep(provider);
      return { value, provider };
    },
  });
  const dialog = [...document.querySelectorAll(".modal-backdrop")].pop();
  const $ = (s) => dialog.querySelector(s);
  function keep(provider) {
    drafts[provider] = { provider, key: $("[data-key]").value, model: $("[data-model]").value, remember: $("[data-remember]").checked };
  }
  function show(provider) {
    const s = drafts[provider] ?? aiSettings(provider);
    const p = PROVIDERS[provider];
    $("[data-key-label]").textContent = `${p.api} key`;
    $("[data-key]").value = s.key;
    $("[data-model]").value = s.model;
    $("#ai-models").innerHTML = p.models.map(([id, name]) => `<option value="${id}">${esc(name)}</option>`).join("");
    $("[data-remember]").checked = s.remember || !s.key;
    $("[data-key-link]").href = p.keyUrl;
    $("[data-key-link]").textContent = `Get a ${p.api} key`;
    const saved = aiSettings(provider).key;
    [...dialog.querySelectorAll(".actions button")].find((b) => b.textContent === "Remove key").style.display = saved ? "" : "none";
  }
  let current = first.provider;
  dialog.querySelectorAll('[name="ai-provider"]').forEach((radio) => {
    radio.onchange = () => { keep(current); current = radio.value; show(current); };
  });
  show(current);

  const result = await pending;
  if (!result) return false;
  if (result.value === "remove") {
    saveAiSettings({ ...aiSettings(result.provider), key: "", remember: false });
    return true;
  }
  // Save every service edited here, the picked one last so it becomes the one in use.
  const order = Object.keys(drafts).filter((p) => p !== result.provider).concat(result.provider);
  for (const p of order) saveAiSettings(drafts[p]);
  return true;
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
    <p>One open-ended question. Work it out on a whiteboard, ask an AI interviewer when stuck, then
      score yourself against a reference design.</p>
    <ul class="track-facts"><li>${plural(questions.length, "question")}</li><li>${limit / 60} min</li><li>self-reviewed</li></ul>
    <div class="track-foot">${status}<span class="track-cta">Open →</span></div>
  </a>`;
}

// ---------------------------------------------------------------- question list
export async function renderDesignHome() {
  const [{ questions }, { session: active }, foundations] = await Promise.all([
    api("GET", "/api/design/questions"), api("GET", "/api/design/active"),
    foundationsSection("design", "Networking and APIs, data, the building blocks, and reliability."),
  ]);
  const preferUnseen = storage("swe-prac-design-prefer-unseen") !== "0";

  const banner = active ? `<div class="banner">
      <div><strong>Session in progress:</strong> ${esc(active.question.title)} · ${active.mode} ·
        <span class="mono">${timerLabel(active.timer)}</span></div>
      <div style="display:flex;gap:8px"><button class="primary" data-resume>Resume</button>
        <button class="danger" data-end-active>End session</button></div>
    </div>` : "";

  const cards = questions.map((q) => {
    const inSession = active && active.question.id === q.id;
    const lock = inSession ? 'disabled title="Locked during a session on this question"' : "";
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
    <p class="lead">One deliberately vague question, ${MINUTES} minutes. Set the scope and design it on a
      whiteboard, then compare with a reference design and tick off what you covered.</p>
    <p class="faint" style="margin:-8px 0 0"><a href="#/design/framework">Framework guide →</a>
      how to pace the round and what interviewers grade.</p>
    ${banner}
    ${foundations}
    <h2 class="section-title">AI interviewer</h2>
    <div class="random-row">
      <span class="dim">Ask for hints during a session: <strong>Strict</strong> answers yes or no;
        <strong>Helpful</strong> gives a few sentences. Every hint shows in the review.</span>
      <span class="faint" data-ai-status>${esc(aiStatus())}</span>
      <button class="small" data-ai-settings>AI settings</button>
    </div>
    <h2 class="section-title">Questions</h2>
    <div class="random-row">
      <button data-random ${active ? "disabled" : ""}>🎲 Random question</button>
      <label><input type="checkbox" data-unseen ${preferUnseen ? "checked" : ""}> Prefer questions I haven't tried</label>
    </div>
    <div class="problem-grid">${cards || '<p class="dim">No questions found in <code>designs/</code>.</p>'}</div>
  </main>`;

  const unseenBox = $app.querySelector("[data-unseen]");
  unseenBox.addEventListener("change", () => storage("swe-prac-design-prefer-unseen", unseenBox.checked ? "1" : "0"));
  $app.querySelector("[data-ai-settings]").onclick = async () => {
    if (await openAiSettings()) $app.querySelector("[data-ai-status]").textContent = aiStatus();
  };

  const start = async (questionId) => {
    const mode = await chooseMode(MINUTES, "the question and the whiteboard");
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

// ---------------------------------------------------------------- hints (session and review)
function hintEntryHtml(h) {
  const mark = h.profile === "strict" ? verdict(h.answer) : null;
  return `<li class="hint-entry ${esc(h.profile)}">
    <div class="hint-meta">${fmtClock(h.at)} · <strong>${esc(PERSONAS[h.profile]?.name ?? h.profile)}</strong>${h.source === "pasted" ? ' · <span class="faint">pasted</span>' : ""}</div>
    <div class="hint-q">${h.question ? esc(h.question) : '<span class="faint">Hint, no question</span>'}</div>
    <div class="hint-a">${mark ? `<span class="verdict ${mark}">${mark === "yes" ? "✓" : "✗"}</span>` : ""}${esc(h.answer)}</div>
  </li>`;
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
  const st = {
    s: session,
    timer: { ...session.timer, syncedAt: performance.now() },
    dirty: false,
    lastSaved: null,
    timeUpShown: storage(`swe-prac-design-timeup-${sessionId}`) === "1",
    persona: PERSONAS[storage("swe-prac-design-persona")] ? storage("swe-prac-design-persona") : "strict",
    asking: false,
    transcribing: null, // {skip()} while a prompt waits for the recording's transcript
    closed: false,
    pending: null, // {profile, question} of a prompt copied for the visitor's own agent
  };

  $app.innerHTML = `<div class="session design-session">
    <div class="session-bar">
      <a href="#/design" class="ghost" title="Back to questions" style="color:var(--text-dim)">←</a>
      <span class="title">${esc(session.question.title)}</span>
      <span class="mode-badge">${session.mode}</span>
      <span class="spacer"></span>
      <span class="save-state" data-save-state></span>
      <span class="rec-status hidden" data-rec-status aria-live="polite"></span>
      <button class="rec-btn ${recordingSupported() ? "" : "hidden"}" data-rec title="Record sound only. It stays in this browser.">● Record</button>
      <span class="timer" data-timer>--:--</span>
      <button data-pause class="${session.mode === "pausable" ? "" : "hidden"}">Pause</button>
      <button data-end class="danger">End session</button>
    </div>
    <div class="workspace" data-workspace>
      <section class="statement-pane side-pane" data-blur>
        <div class="prompt-card">
          <span class="num">QUESTION ${session.question.number}</span>
          <h2>${esc(session.question.title)}</h2>
          <p>${esc(session.question.prompt)}</p>
        </div>
        <div class="ask-pane">
          <h3 class="ask-title">AI interviewer</h3>
          <div class="persona-pick" role="radiogroup" aria-label="Interviewer">
            ${Object.entries(PERSONAS).map(([k, p]) => `<button class="persona" role="radio" data-persona="${k}">
              <strong>${p.name}</strong><span>${p.blurb}</span></button>`).join("")}
          </div>
          <ol class="hint-log" data-log></ol>
          <div class="ask-form">
            <textarea data-ask rows="2" placeholder="Ask a question, or leave it blank for a hint (Ctrl+Enter)"></textarea>
            <div class="ask-actions">
              <button class="primary" data-send>Ask</button>
              <span class="ask-status" data-ask-status></span>
              <button class="ghost small hidden" data-skip title="Go on without the transcript">Skip</button>
              <button class="ghost small" data-ai-settings>AI settings</button>
            </div>
            <div class="paste-back hidden" data-paste>
              <textarea data-reply rows="3" placeholder="Paste your AI agent's reply"></textarea>
              <div class="ask-actions"><button class="primary small" data-save-reply>Add reply</button>
                <button class="ghost small" data-cancel-paste>Cancel</button></div>
            </div>
            <p class="faint ask-mode" data-ask-mode></p>
          </div>
        </div>
      </section>
      <div class="gutter" data-gutter-x></div>
      <section class="board-pane" data-blur><div class="board-host" data-board-host></div></section>
    </div>
  </div>`;
  const q = (sel) => $app.querySelector(sel);
  const workspace = q("[data-workspace]");

  // ----- the whiteboard
  const markDirty = () => { st.dirty = true; renderSaveState(); };
  const board = createWhiteboard(q("[data-board-host]"), session.board, { onChange: markDirty });
  const work = () => ({ board: board.getModel() });

  // ----- saving
  function renderSaveState() {
    const el = q("[data-save-state]");
    if (el) el.textContent = st.dirty ? "Unsaved…" : st.lastSaved ? "Saved" : "";
  }
  async function save() {
    if (!st.dirty || st.timer.paused) return;
    st.dirty = false;
    try {
      const res = await api("PUT", `/api/design/sessions/${sessionId}/board`, work());
      st.lastSaved = Date.now();
      if (res?.timer) syncTimer(res.timer);
    } catch (err) {
      st.dirty = true;
      if (err.status !== 409) toast(`Autosave failed: ${err.message}`, "bad");
    }
    renderSaveState();
  }
  const autosave = setInterval(save, 3000);
  const beforeUnload = (e) => {
    save();
    if (recorder?.state() === "recording") { e.preventDefault(); e.returnValue = ""; }
  };
  window.addEventListener("beforeunload", beforeUnload);

  // ----- recording (sound only)
  const recorder = recordingSupported()
    ? createRecorder({ sessionId, elapsed: () => currentElapsed(), onChange: () => { renderRec(); transcriber?.recordingChanged(); } })
    : null;
  // Transcribes the recording while it's made, for the interviewer's prompts.
  const transcriber = recorder && transcriptionSupported() ? createTranscriber({ sessionId, recorder }) : null;
  function renderRec() {
    const btn = q("[data-rec]");
    if (!btn || !recorder) return;
    const state = recorder.state();
    btn.classList.toggle("on", state !== "inactive");
    btn.classList.toggle("held", state === "paused");
    btn.textContent = state === "inactive" ? "● Record" : `${state === "paused" ? "⏸" : "■"} ${fmtClock(recorder.seconds())}`;
    btn.title = state === "inactive" ? "Record sound only. It stays in this browser." : "Stop recording";
    btn.disabled = st.timer.paused && state === "inactive";
  }
  // Loads the speech model picked for a recording, at once (the microphone may still be asking),
  // with its progress beside the Record button. Once loaded it stays loaded for the page.
  const loadedModels = new Set(); // ids
  let lastLoad = 0;
  async function loadSpeech(model) {
    if (loadedModels.has(model.id)) return;
    const el = q("[data-rec-status]");
    const mine = ++lastLoad;
    const show = (text) => {
      if (st.closed || mine !== lastLoad) return;
      el.textContent = text;
      el.classList.toggle("hidden", !text);
    };
    const saved = await modelSaved(model);
    const loading = "Loading speech model…";
    show(saved ? loading : `Downloading speech model… 0 of ${model.mb} MB`);
    try {
      await transcriber.load(model, (loaded) => {
        const mb = Math.floor(loaded / 1e6);
        if (!saved) show(mb < model.mb ? `Downloading speech model… ${mb} of ${model.mb} MB` : loading);
      });
      loadedModels.add(model.id);
      show("Speech model ready");
      setTimeout(() => show(""), 4000);
    } catch (err) {
      show("");
      if (!st.closed) toast(err.message, "bad");
    }
  }
  q("[data-rec]").onclick = async () => {
    if (!recorder) return;
    try {
      if (recorder.state() === "inactive") {
        if (st.timer.paused) return;
        const speech = transcriber ? await chooseSpeech() : null;
        if (transcriber && !speech) return;
        if (st.timer.paused || recorder.state() !== "inactive") return; // paused while choosing
        if (speech) loadSpeech(MODELS[speech]);
        await recorder.start(speech ? { speech } : {});
        toast("Recording sound. Stop it any time; it plays back in the review.", "good");
      } else {
        await recorder.stop();
        toast("Recording saved in this browser.");
      }
    } catch (err) { toast(err.message, "bad"); }
    renderRec();
  };

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
    if (recorder && recorder.state() !== "inactive") renderRec();
  }
  const tick = setInterval(renderTimer, 250);
  const resync = setInterval(async () => {
    try { syncTimer(await api("GET", `/api/design/sessions/${sessionId}/timer`)); } catch { /* offline */ }
  }, 15000);

  async function showTimeUp() {
    const choice = await modal({
      title: "⏰ Time's up",
      body: "<p>A real interview ends here. Keep going in overtime, or end and review.</p>",
      actions: [{ label: "Keep going (overtime)", value: "keep", kind: "ghost" }, { label: "End & review", value: "end", kind: "primary" }],
    });
    if (choice === "end") await endSession(false);
  }

  // ----- the interviewer
  const askBox = q("[data-ask]");
  const replyBox = q("[data-reply]");
  let notes = null; // the question's interviewer notes, fetched for the first API hint
  const status = (text, bad = false) => {
    const el = q("[data-ask-status]");
    el.textContent = text;
    el.classList.toggle("fail", bad);
  };
  function renderAsk() {
    const { key } = aiSettings();
    const paused = st.timer.paused;
    $app.querySelectorAll("[data-persona]").forEach((b) => {
      b.classList.toggle("on", b.dataset.persona === st.persona);
      b.setAttribute("aria-checked", String(b.dataset.persona === st.persona));
    });
    const send = q("[data-send]");
    send.textContent = st.asking ? "Asking…" : st.transcribing ? "Transcribing…" : key ? "Ask" : "Copy prompt";
    send.disabled = Boolean(st.asking || st.transcribing || paused);
    askBox.disabled = paused;
    q("[data-skip]").classList.toggle("hidden", !st.transcribing);
    q("[data-ask-mode]").textContent = key
      ? `${aiStatus()}. Requests include a transcript of any recording.`
      : "No API key: Copy prompt puts the request, with a transcript of any recording, on your clipboard for any AI agent. Paste its reply back here.";
  }
  function renderLog() {
    const log = q("[data-log]");
    log.innerHTML = st.s.asked.length
      ? st.s.asked.map(hintEntryHtml).join("")
      : `<li class="hint-empty faint">Pick an interviewer and ask. A blank question asks for a hint on where you are.</li>`;
    log.scrollTop = log.scrollHeight;
  }
  const context = () => ({
    question: st.s.question,
    elapsed: currentElapsed(),
    limit: st.timer.limit,
    board: board.getModel(),
    hints: st.s.asked,
  });
  async function logHint(hint) {
    const res = await api("POST", `/api/design/sessions/${sessionId}/hints`, hint);
    st.s.asked = res.asked;
    renderLog();
    renderAsk();
  }

  async function ask() {
    if (st.asking || st.transcribing || st.timer.paused) return;
    const settings = aiSettings();
    const question = askBox.value.trim();
    const persona = st.persona;
    if (!settings.key) { await copyPrompt(persona, question); return; }
    const said = await transcriptForPrompt();
    if (st.closed) return;
    st.asking = true;
    status("Thinking…");
    renderAsk();
    try {
      notes ??= await api("GET", `/api/design/sessions/${sessionId}/interviewer`);
      const user = userPrompt({ ...context(), transcript: said.lines }, question);
      const { text } = await askApi(settings, { system: systemPrompt(persona, notes), user });
      await logHint({ profile: persona, question, answer: text, source: "api" });
      askBox.value = "";
      status("");
    } catch (err) {
      status(err.message, true);
    } finally {
      st.asking = false;
      renderAsk();
    }
  }

  // The session's recordings as text for the interviewer's prompt, transcribed in this browser.
  // {lines: [{at, text}] or null when the prompt goes without, note: for the status line}.
  async function transcriptForPrompt() {
    let clips = [];
    try { clips = await listClips(sessionId); } catch { /* recordings unavailable: none to add */ }
    if (!clips.length) return { lines: null, note: "" };
    if (!transcriber) return { lines: null, note: " without a transcript (this browser can't make one)" };
    const pct = (part, whole) => `${whole > 0 ? Math.min(100, Math.round((100 * part) / whole)) : 0}%`;
    const progress = (p) => {
      if (st.transcribing !== job) return; // skipped: it still finishes, saved for next time
      status(p.phase === "load"
        ? `Loading the speech model (${p.mb} MB the first time)… ${pct(p.loaded, p.mb * 1e6)}`
        : `Transcribing your recording… ${pct(p.done, p.total)}`);
    };
    let skip;
    const skipped = new Promise((resolve) => { skip = () => resolve("skip"); });
    const job = { skip };
    st.transcribing = job;
    status("Transcribing your recording…");
    renderAsk();
    try {
      const lines = await Promise.race([transcriber.transcript({ onProgress: progress }), skipped]);
      if (lines === "skip") return { lines: null, note: " without the transcript" };
      return { lines, note: lines?.length ? " with your recording's transcript" : " (nothing heard in your recording yet)" };
    } catch (err) {
      if (!st.closed) toast(err.message, "bad");
      return { lines: null, note: " without the transcript" };
    } finally {
      st.transcribing = null;
      if (!st.closed) renderAsk();
    }
  }

  async function copyPrompt(persona, question) {
    const said = await transcriptForPrompt();
    if (st.closed) return;
    const text = pastePrompt(persona, { ...context(), transcript: said.lines }, question);
    let copied = true;
    try { await navigator.clipboard.writeText(text); } catch { copied = false; }
    if (!copied) {
      // A long transcription can outlast the click's permission to write the clipboard: this
      // button is a fresh click.
      const shown = modal({
        title: "Copy this prompt",
        body: `<p>Paste it into your AI agent, then paste the reply back.</p>
          <textarea class="prompt-copy" readonly rows="12">${esc(text)}</textarea>
          <p style="margin-bottom:0"><button class="small" data-copy-prompt>Copy</button></p>`,
        actions: [{ label: "Done", value: true, kind: "primary" }],
      });
      const dialog = [...document.querySelectorAll(".modal-backdrop")].pop();
      dialog.querySelector("[data-copy-prompt]").onclick = async (e) => {
        try {
          await navigator.clipboard.writeText(text);
          e.target.textContent = "Copied";
        } catch {
          const box = dialog.querySelector(".prompt-copy");
          box.focus();
          box.select();
        }
      };
      await shown;
    }
    st.pending = { profile: persona, question };
    q("[data-paste]").classList.remove("hidden");
    replyBox.focus();
    status(copied ? `Copied${said.note}. Paste it into your AI agent, then paste the reply below.` : "");
  }
  async function saveReply() {
    const answer = replyBox.value.trim();
    if (!answer || !st.pending) return;
    try {
      await logHint({ ...st.pending, answer, source: "pasted" });
      replyBox.value = "";
      askBox.value = "";
      st.pending = null;
      q("[data-paste]").classList.add("hidden");
      status("");
    } catch (err) { status(err.message, true); }
  }

  $app.querySelectorAll("[data-persona]").forEach((b) => {
    b.onclick = () => { st.persona = b.dataset.persona; storage("swe-prac-design-persona", st.persona); renderAsk(); };
  });
  q("[data-send]").onclick = ask;
  q("[data-skip]").onclick = () => st.transcribing?.skip();
  askBox.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); ask(); }
  });
  q("[data-save-reply]").onclick = saveReply;
  q("[data-cancel-paste]").onclick = () => { st.pending = null; replyBox.value = ""; q("[data-paste]").classList.add("hidden"); status(""); };
  // Setting up the AI isn't interview time: a pausable session pauses first, so the Paused card
  // sits behind the dialog, and stays paused after it closes. A strict session's clock runs on.
  q("[data-ai-settings]").onclick = async () => {
    if (session.mode === "pausable" && !st.timer.paused && currentElapsed() < st.timer.limit) await setPaused(true);
    if (await openAiSettings()) { status(""); renderAsk(); }
  };

  // ----- pausing
  function applyPaused() {
    const paused = st.timer.paused;
    $app.querySelectorAll("[data-blur]").forEach((el) => el.classList.toggle("blurred", paused));
    board.setReadOnly(paused);
    if (recorder) { if (paused) recorder.pause(); else recorder.resume(); }
    renderRec();
    renderAsk();
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
  }
  async function setPaused(paused) {
    if (paused === Boolean(st.timer.paused)) return;
    try {
      if (paused) await save();
      syncTimer(await api("POST", `/api/design/sessions/${sessionId}/${paused ? "pause" : "resume"}`));
      applyPaused();
    } catch (err) { toast(err.message, "bad"); }
  }
  const togglePause = () => setPaused(!st.timer.paused);

  async function endSession(askFirst = true) {
    if (askFirst && !(await confirmEnd())) return;
    try {
      await recorder?.stop();
      await api("POST", `/api/design/sessions/${sessionId}/end`, st.timer.paused ? undefined : work());
      st.dirty = false;
      location.hash = `#/design/review/${sessionId}`;
    } catch (err) { toast(err.message, "bad"); }
  }

  q("[data-pause]").onclick = togglePause;
  q("[data-end]").onclick = () => endSession(true);
  const keyHandler = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); }
  };
  window.addEventListener("keydown", keyHandler);
  resizableSplit(workspace, q("[data-gutter-x]"));

  renderLog();
  renderTimer();
  applyPaused();
  if (!st.timer.paused) board.focus();

  return async () => {
    st.closed = true;
    transcriber?.stop();
    await save();
    await recorder?.stop().catch(() => {});
    clearInterval(autosave); clearInterval(tick); clearInterval(resync);
    window.removeEventListener("beforeunload", beforeUnload);
    window.removeEventListener("keydown", keyHandler);
    board.dispose();
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

// Sessions from before the whiteboard kept notes per step: [{title, text}].
function notesHtml(notes) {
  if (!notes?.length) return "";
  return `<h3>Your notes</h3>${notes.map((n) => `<div class="notes-block"><h4>${esc(n.title)}</h4>
    <pre>${esc(n.text)}</pre></div>`).join("")}`;
}

// The board at full size, over the page; click or Esc closes it.
function showBoardFull(svg) {
  const wrap = document.createElement("div");
  wrap.className = "board-full";
  wrap.tabIndex = -1;
  wrap.innerHTML = `<div class="board-full-bar"><span>Your board</span><button class="small" data-close>Close</button></div>
    <div class="board-full-body">${svg.replace('style="max-width:100%;height:auto"', "")}</div>`;
  const close = () => wrap.remove();
  wrap.querySelector("[data-close]").onclick = close;
  wrap.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  document.body.appendChild(wrap);
  wrap.focus();
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
  const hints = data.asked;
  const byPersona = Object.keys(PERSONAS).map((k) => [k, hints.filter((h) => h.profile === k).length]).filter(([, n]) => n);

  $app.innerHTML = `${topnav("")}<main class="page">
    <p class="faint" style="margin:0 0 4px"><a href="#/history">← History</a></p>
    <h1>${esc(data.question.title)}</h1>
    <p class="lead">${data.mode === "strict" ? "Strict" : "Pausable"} system design session · ${fmtDate(data.started_at)}</p>
    <div class="stat-grid">
      <div class="stat"><div class="label">Time used</div>
        <div class="value">${fmtClock(Math.min(r.elapsed, r.time_limit))}</div>
        <div class="sub">${r.overtime_seconds > 0 ? `+ ${fmtClock(r.overtime_seconds)} overtime` : `of ${fmtClock(r.time_limit)}`}</div></div>
      <div class="stat"><div class="label">Self-review</div>
        <div class="value" data-score>${scoreText(data.score)}</div>
        <div class="sub" data-score-sub></div></div>
      <div class="stat"><div class="label">Hints asked</div>
        <div class="value">${hints.length}</div>
        <div class="sub">${byPersona.length ? byPersona.map(([k, n]) => `${n} ${PERSONAS[k].name.toLowerCase()}`).join(" · ") : "none"}</div></div>
      <div class="stat"><div class="label">Pauses</div>
        <div class="value">${r.pauses.count}</div>
        <div class="sub">${r.pauses.count ? `${fmtClock(r.pauses.total_seconds)} paused` : data.mode === "strict" ? "strict mode" : "none taken"}</div></div>
    </div>
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
    ["board", "Your board"],
    ["hints", `Interviewer${hints.length ? ` <span class="badge">${hints.length}</span>` : ""}`],
    ["recording", "Recording"],
    ["reference", "Reference design"],
  ];
  let current = "assess";
  const panel = $app.querySelector("[data-review-panel]");
  const urls = []; // object URLs of the recordings shown, freed when the panel changes
  const freeUrls = () => { while (urls.length) URL.revokeObjectURL(urls.pop()); };
  const boardSvg = renderBoardSvg(data.board);
  const fileSize = (bytes) => (bytes < 1048576 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1048576).toFixed(1)} MB`);

  async function showRecordings() {
    let clips;
    try { clips = await listClips(sessionId); } catch { clips = null; }
    if (current !== "recording") return;
    if (!clips) { panel.innerHTML = '<p class="dim">This browser can\'t open its saved recordings.</p>'; return; }
    if (!clips.length) {
      panel.innerHTML = '<p class="dim">No recording. Press ● Record during a session to capture sound only.</p>';
      return;
    }
    const blobs = await Promise.all(clips.map((c) => clipBlob(c)));
    if (current !== "recording") return;
    const slug = data.question.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    panel.innerHTML = `<p class="dim" style="margin-top:0">Saved in this browser only, and not part of the history export. Download to keep a copy.</p>
      <ul class="clips">${clips.map((c, i) => {
        const url = URL.createObjectURL(blobs[i]);
        urls.push(url);
        const name = `${slug}-${fmtDate(data.started_at).replace(/[^\w]+/g, "-")}-${i + 1}.${clipExtension(c.mime)}`;
        return `<li class="clip">
          <div class="clip-meta"><strong>Recording ${i + 1}</strong> · started at ${fmtClock(c.started_at)} ·
            ${fmtClock(c.duration)} long · ${fileSize(blobs[i].size)}</div>
          <audio controls preload="metadata" src="${url}"></audio>
          <div class="clip-actions"><a class="button-link" href="${url}" download="${esc(name)}">Download</a>
            <button class="small danger" data-delete-clip="${esc(c.id)}">Delete</button></div>
        </li>`;
      }).join("")}</ul>`;
    panel.querySelectorAll("[data-delete-clip]").forEach((b) => {
      b.onclick = async () => {
        const ok = await modal({
          title: "Delete this recording?",
          body: "<p>It's removed from this browser for good.</p>",
          actions: [{ label: "Cancel", value: false, kind: "ghost" }, { label: "Delete", value: true, kind: "danger" }],
        });
        if (!ok) return;
        await deleteClip(b.dataset.deleteClip);
        freeUrls();
        showRecordings();
      };
    });
  }

  function show(key) {
    current = key;
    freeUrls();
    $app.querySelector("[data-review-tabs]").innerHTML = tabs.map(([k, label]) =>
      `<button class="tab ${k === current ? "active" : ""}" data-k="${k}">${label}</button>`).join("");
    $app.querySelectorAll("[data-k]").forEach((b) => { b.onclick = () => show(b.dataset.k); });
    panel.className = "review-panel";
    if (key === "assess") {
      panel.innerHTML = `<p class="dim" style="margin-top:0">Grade yourself: tick only what your board shows.
        Ticks save as you go.</p>
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
    } else if (key === "board") {
      const notes = notesHtml(data.notes);
      panel.innerHTML = boardSvg
        ? `<div style="margin:0 0 8px"><button class="small" data-full>Full size</button></div>
          <div class="board-view" data-full-view title="Open at full size">${boardSvg}</div>${notes}`
        : notes || '<p class="dim">You didn\'t use the whiteboard in this session.</p>';
      panel.querySelectorAll("[data-full], [data-full-view]").forEach((el) => { el.onclick = () => showBoardFull(boardSvg); });
    } else if (key === "hints") {
      panel.innerHTML = hints.length
        ? `<ol class="hint-log review">${hints.map(hintEntryHtml).join("")}</ol>`
        : '<p class="dim">You didn\'t ask the interviewer in this session.</p>';
    } else if (key === "recording") {
      panel.innerHTML = '<p class="dim">Loading…</p>';
      showRecordings();
    } else {
      panel.className = "review-panel md";
      panel.innerHTML = hintsHtml(data.hints) + data.reference_html;
    }
  }
  show(current);
  return async () => { current = null; freeUrls(); };
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
        ? `${hintsHtml(data.hints)}<p class="dim">These say where the difficulty is, not how to solve it.</p>`
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
      <td>${s.status === "active" ? '<span class="chip">in progress</span>' : scoreText(s.score)}</td>
      <td>${s.asked || "—"}</td>
      <td>${fmtClock(Math.min(s.elapsed, s.time_limit))}${over}</td>
      <td>${s.pauses.count ? `${s.pauses.count} (${fmtClock(s.pauses.total_seconds)})` : "—"}</td>
    </tr>`;
  }).join("");
  return `<table class="table"><tr><th>Date</th><th>Question</th><th>Mode</th><th>Self-review</th><th>Hints</th><th>Time</th><th>Pauses</th></tr>${rows}</table>`;
}
