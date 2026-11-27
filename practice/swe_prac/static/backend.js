// The app's backend, in the browser. There is no server: every api() call (common.js) lands in
// handle() below, and the answers have the shapes the pages expect.
//
//   sessions, timers, scoring    kept in localStorage (one key, all three tracks)
//   questions and study pages    data.json, built by tools/build_static.py
//   each problem's tests         tests/coding/<id>.json and tests/algo/<id>.json
//   Run, Submit, Run scratch     Python in a Web Worker (python.js)
//   lint and Format              ruff compiled to WebAssembly (lint.js)
//
// createBackend() takes those as dependencies so tests/js/ can drive it with fakes.
import * as python from "./python.js";
import * as ruff from "./lint.js";

const STORAGE_KEY = "swe-prac-static-v1"; // the name predates the in-browser runner; kept so old sessions load
const BACKUP_FORMAT = "swe-prac-history";

export class ApiError extends Error {
  constructor(message, status = 409) {
    super(message);
    this.status = status;
  }
}

function browserDeps() {
  const url = (path) => new URL(path, document.baseURI);
  return {
    fetchJson: async (path) => {
      const res = await fetch(url(path));
      if (!res.ok) throw new ApiError(`Could not load ${path} (${res.status})`, 500);
      return res.json();
    },
    fetchText: async (path) => {
      const res = await fetch(url(path));
      if (!res.ok) throw new ApiError(`Could not load ${path} (${res.status})`, 500);
      return res.text();
    },
    storage: {
      get: () => localStorage.getItem(STORAGE_KEY),
      set: (text) => localStorage.setItem(STORAGE_KEY, text),
    },
    python,
    ruff,
    clock: () => Date.now() / 1000,
    random: Math.random,
    onStorageError: (message) => window.dispatchEvent(new CustomEvent("swe-storage", { detail: message })),
  };
}

export function createBackend(deps) {
  const { fetchJson, fetchText, storage, clock, random } = deps;

  // ---------------------------------------------------------------- data
  let bundle = null; // data.json
  let bundleLoad = null;
  const testFiles = new Map(); // "coding/<id>" -> the problem's tests file

  async function loadBundle() {
    bundleLoad ??= fetchJson("data.json").then((data) => { bundle = data; });
    await bundleLoad;
  }

  // Every test of a problem, shown and hidden: fetched the first time it runs.
  async function testsFile(track, id) {
    const key = `${track}/${id}`;
    if (!testFiles.has(key)) {
      const load = fetchJson(`tests/${key}.json`);
      testFiles.set(key, load);
      load.catch(() => testFiles.delete(key));
    }
    return testFiles.get(key);
  }

  let helpersText = null; // helpers.py for algorithm scratch runs
  const helpers = async () => (helpersText ??= await fetchText("py/helpers.py"));

  function problemData(problemId) {
    const found = bundle.problems.find((p) => p.problem.id === problemId);
    if (!found) throw new ApiError(`Unknown problem '${problemId}'`, 404);
    return found;
  }

  // ---------------------------------------------------------------- storage
  let state = { nextId: 1, sessions: [] };
  let storageWarned = false;

  // Re-read on every request so two open tabs don't overwrite each other. If storage is
  // unavailable (some private modes), the in-memory copy carries on for this page load.
  function readState() {
    try {
      const raw = storage.get();
      if (raw) state = JSON.parse(raw);
    } catch { /* keep the in-memory state */ }
  }

  function persist() {
    try {
      storage.set(JSON.stringify(state));
    } catch (err) {
      if (!storageWarned) {
        storageWarned = true;
        deps.onStorageError?.(`Your work isn't being saved: this browser refused to store it (${err.message}). Export your history from the History page to keep it.`);
      }
    }
  }

  function getSession(id) {
    const s = state.sessions.find((x) => x.id === id);
    if (!s) throw new ApiError("Session not found.", 404);
    return s;
  }

  const activeSession = () => [...state.sessions].reverse().find((s) => s.status === "active") ?? null;

  // ---------------------------------------------------------------- timer (all three tracks)
  // Elapsed time is wall clock minus recorded pauses, so reloading or closing the tab changes
  // nothing: a strict session's clock keeps running.
  function elapsed(s, now = clock()) {
    if (s.status === "finished") return s.final_elapsed;
    const end = s.paused_at !== null ? s.paused_at : now;
    return Math.max(0, end - s.started_at - s.total_paused);
  }

  function timerState(s) {
    const spent = elapsed(s);
    return {
      elapsed: spent,
      limit: s.time_limit,
      remaining: Math.max(0, s.time_limit - spent),
      overtime: spent >= s.time_limit,
      paused: s.paused_at !== null,
      status: s.status,
      mode: s.mode,
    };
  }

  function requireEditable(s) {
    if (s.status !== "active") throw new ApiError("This session has ended.");
    if (s.paused_at !== null) throw new ApiError("The session is paused. Resume to continue.");
  }

  function saveCode(s, body) {
    requireEditable(s);
    if (body?.code != null) s.code = body.code;
    if (body?.scratch != null) s.scratch = body.scratch;
  }

  function pause(s) {
    if (s.mode !== "pausable") throw new ApiError("This is a strict session: the timer cannot be paused.");
    requireEditable(s);
    const now = clock();
    if (elapsed(s, now) >= s.time_limit) {
      throw new ApiError("Time is up; overtime is untimed, so there is nothing to pause.");
    }
    s.pauses.push({ started_at: now, ended_at: null, start_elapsed: elapsed(s, now) });
    s.paused_at = now;
  }

  function resume(s) {
    if (s.status !== "active") throw new ApiError("This session has ended.");
    if (s.paused_at === null) throw new ApiError("The session is not paused.");
    const now = clock();
    s.total_paused += now - s.paused_at;
    s.paused_at = null;
    for (const p of s.pauses) if (p.ended_at === null) p.ended_at = now;
  }

  function finish(s) {
    if (s.status !== "active") throw new ApiError("This session has already ended.");
    if (s.paused_at !== null) resume(s);
    const now = clock();
    s.final_elapsed = elapsed(s, now);
    s.finished_at = now;
    s.status = "finished";
  }

  // Count and total length of pauses; one still open counts up to now.
  function pauseSummary(pauses) {
    const now = clock();
    return {
      count: pauses.length,
      total_seconds: pauses.reduce((sum, p) => sum + (p.ended_at ?? now) - p.started_at, 0),
    };
  }

  const pick = (pool) => pool[Math.floor(random() * pool.length)];

  // ---------------------------------------------------------------- running code
  const lintSettings = (track) => bundle.ruff[track];

  async function lintCode(code, track) {
    try {
      return await deps.ruff.lint(code, lintSettings(track));
    } catch (err) {
      return { issues: [], error: `Lint is unavailable: ${err.message}` };
    }
  }

  const tooSlow = (result) => Boolean(result && !result.passed && (result.error ?? "").startsWith("Too slow"));

  // ---------------------------------------------------------------- coding results
  // Pass counts for one level's own tests from the last submit (optionally before a time).
  function levelRatio(subs, level, before) {
    for (const sub of [...subs].reverse()) {
      if (sub.kind !== "submit" || sub.level !== level) continue;
      if (before != null && sub.elapsed > before) continue;
      const counts = sub.breakdown[String(level)];
      if (counts) {
        return {
          passed: counts.shown_passed + counts.hidden_passed,
          total: counts.shown_total + counts.hidden_total,
          shown_passed: counts.shown_passed,
          shown_total: counts.shown_total,
          hidden_passed: counts.hidden_passed,
          hidden_total: counts.hidden_total,
        };
      }
    }
    return null;
  }

  // Score summary: the timed result (at the limit) and the final one (including overtime).
  function results(s) {
    const limit = s.time_limit;
    const subs = s.submissions ?? [];
    const times = Object.values(s.completions);
    const timedLevels = times.filter((t) => t <= limit).length;
    const finalLevels = times.length;
    const total = bundle.levels.length;
    let previous = 0;
    const levels = bundle.levels.map((level) => {
      const t = s.completions[level] ?? null;
      const row = {
        level,
        completed_at: t,
        split: t === null ? null : t - previous,
        target: bundle.pacing[level],
        delta: t === null ? null : t - bundle.pacing[level],
        overtime: t !== null && t > limit,
      };
      if (t !== null) previous = t;
      return row;
    });
    const timedStop = timedLevels < total ? timedLevels + 1 : null;
    const finalStop = finalLevels < total ? finalLevels + 1 : null;
    const spent = elapsed(s);
    return {
      time_limit: limit,
      elapsed: spent,
      overtime_seconds: Math.max(0, spent - limit),
      timed: {
        levels_completed: timedLevels,
        stopped_level: timedStop,
        stopped_level_ratio: timedStop ? levelRatio(subs, timedStop, limit) : null,
      },
      final: {
        levels_completed: finalLevels,
        stopped_level: finalStop,
        stopped_level_ratio: finalStop ? levelRatio(subs, finalStop, null) : null,
      },
      levels,
      pauses: pauseSummary(s.pauses),
      runs: subs.filter((x) => x.kind === "run").length,
      submits: subs.filter((x) => x.kind === "submit").length,
    };
  }

  // Full detail for the shown tests; counts per level for the hidden ones.
  function summarizeCoding(tests, run) {
    const shown = [];
    const breakdown = {};
    let allPassed = run.import_error === null && run.crashed === null;
    for (const test of tests) {
      const result = run.results[test.id] ?? null;
      const passed = Boolean(result?.passed);
      allPassed &&= passed;
      const counts = (breakdown[String(test.level)] ??= { shown_passed: 0, shown_total: 0, hidden_passed: 0, hidden_total: 0 });
      counts[`${test.visibility}_total`] += 1;
      counts[`${test.visibility}_passed`] += passed ? 1 : 0;
      if (test.visibility === "shown") {
        shown.push({
          id: test.id,
          level: test.level,
          name: test.name,
          passed,
          ran: result !== null,
          steps: result?.steps ?? [],
          total_steps: test.steps.length,
          failed_step: result?.failed_step ?? null,
          error: result?.error ?? null,
          stdout: result?.stdout ?? "",
          ms: result?.ms ?? null,
        });
      }
    }
    return { shown, breakdown, allPassed };
  }

  // ---------------------------------------------------------------- coding endpoints
  function sessionPayload(s) {
    const data = problemData(s.problem_id);
    const unlocked = Math.min(s.current_level, bundle.levels.length);
    return {
      id: s.id,
      problem: data.problem,
      mode: s.mode,
      status: s.status,
      current_level: s.current_level,
      all_levels_done: s.current_level > bundle.levels.length,
      levels: data.levels.slice(0, unlocked).map((lv) => ({
        ...lv,
        completed_at: s.completions[lv.level] ?? null,
      })),
      code: s.code,
      scratch: s.scratch,
      tests_source: data.tests_source[String(unlocked)],
      timer: timerState(s),
      pacing: bundle.pacing,
      conventions_html: bundle.conventions_html,
    };
  }

  function levelSummaries(data) {
    return data.levels.map(({ level, title, statement_html }) => ({ level, title, statement_html }));
  }

  const endpoints = {
    listProblems() {
      const attempts = {};
      const best = {};
      for (const s of state.sessions) {
        attempts[s.problem_id] = (attempts[s.problem_id] ?? 0) + 1;
        if (s.status === "finished") {
          best[s.problem_id] = Math.max(best[s.problem_id] ?? 0, results(s).timed.levels_completed);
        }
      }
      return {
        problems: bundle.problems.map(({ problem }) => ({
          ...problem,
          attempts: attempts[problem.id] ?? 0,
          best_timed_levels: best[problem.id] ?? null,
        })),
        time_limit: bundle.time_limit,
        pacing: bundle.pacing,
      };
    },

    // The full question, design hints or reference solution, outside any session. Refused while
    // a session on this problem is running, so a live timed attempt can't peek.
    study(problemId, kind) {
      if (!["question", "hints", "reference"].includes(kind)) {
        throw new ApiError(`Unknown view '${kind}'`, 404);
      }
      const data = problemData(problemId);
      const live = activeSession();
      if (live && live.problem_id === problemId) {
        throw new ApiError("This problem is in a running session. End the session to open it.");
      }
      const out = { problem: data.problem, kind };
      if (kind === "question") {
        out.conventions_html = bundle.conventions_html;
        out.levels = levelSummaries(data);
      } else if (kind === "hints") {
        out.hints_html = data.hints_html;
      } else {
        out.reference_code = data.reference_code;
      }
      return out;
    },

    active() {
      const s = activeSession();
      if (!s) return { session: null };
      return {
        session: {
          id: s.id,
          problem: problemData(s.problem_id).problem,
          mode: s.mode,
          current_level: s.current_level,
          timer: timerState(s),
        },
      };
    },

    start({ problem_id: problemId, mode, prefer_unseen: preferUnseen = true }) {
      if (!bundle.problems.length) throw new ApiError("No problems are built. Run tools/build_problem.py --all.", 500);
      if (!["strict", "pausable"].includes(mode)) throw new ApiError("Mode must be 'strict' or 'pausable'.", 400);
      let data;
      if (problemId == null) {
        let pool = bundle.problems;
        if (preferUnseen) {
          const seen = new Set(state.sessions.map((s) => s.problem_id));
          const unseen = pool.filter((p) => !seen.has(p.problem.id));
          if (unseen.length) pool = unseen;
        }
        data = pick(pool);
      } else {
        data = problemData(problemId);
      }
      if (activeSession()) throw new ApiError("Finish or end your active session before starting another.");
      const s = {
        id: state.nextId++,
        problem_id: data.problem.id,
        mode,
        status: "active",
        started_at: clock(),
        time_limit: bundle.time_limit,
        paused_at: null,
        total_paused: 0,
        current_level: 1,
        code: data.starter_code,
        scratch: data.scratch_starter,
        finished_at: null,
        final_elapsed: null,
        completions: {},
        pauses: [],
        submissions: [],
      };
      state.sessions.push(s);
      return sessionPayload(s);
    },

    session(id) {
      const s = getSession(id);
      if (s.status !== "active") throw new ApiError("This session has ended; open its review instead.", 410);
      return sessionPayload(s);
    },

    timer: (id) => timerState(getSession(id)),

    save(id, body) {
      const s = getSession(id);
      saveCode(s, body);
      return { ok: true, timer: timerState(s) };
    },

    pause(id) {
      const s = getSession(id);
      pause(s);
      return timerState(s);
    },

    resume(id) {
      const s = getSession(id);
      resume(s);
      return timerState(s);
    },

    // Run (the shown tests of levels 1..current) or Submit (hidden ones too). A submit that
    // passes everything completes the current level and unlocks the next.
    async execute(id, kind, body) {
      let s = getSession(id);
      saveCode(s, body);
      persist();
      const { code, problem_id: problemId } = s;
      const level = Math.min(s.current_level, bundle.levels.length);
      const file = await testsFile("coding", problemId);
      const tests = file.tests.filter((t) => t.level <= level && (kind === "submit" || t.visibility === "shown"));
      const run = await deps.python.runTests({ code, className: file.class_name, tests });
      const lint = await lintCode(code, "coding");
      const { shown, breakdown, allPassed } = summarizeCoding(tests, run);

      readState(); // the run took a while: build on what's stored now
      s = getSession(id);
      (s.submissions ??= []).push({
        kind, level, elapsed: elapsed(s), at: clock(), all_passed: allPassed, breakdown, lint_count: lint.issues.length,
      });
      let unlocked = null;
      if (kind === "submit" && allPassed && s.current_level === level && level <= bundle.levels.length) {
        s.completions[level] ??= elapsed(s);
        s.current_level = level + 1;
        unlocked = { completed: level, new_level: level + 1 };
      }
      persist();
      return {
        kind,
        level,
        all_passed: allPassed,
        import_error: run.import_error,
        import_stdout: run.import_stdout,
        crashed: run.crashed,
        timed_out: run.timed_out,
        ms: run.ms,
        shown,
        breakdown, // hidden tests: counts only, never inputs or outputs
        lint,
        unlocked,
        session: unlocked ? sessionPayload(s) : null,
      };
    },

    run: (id, body) => endpoints.execute(id, "run", body),
    submit: (id, body) => endpoints.execute(id, "submit", body),

    async scratch(id, body) {
      const s = getSession(id);
      saveCode(s, body);
      persist();
      return deps.python.runScratch({ code: s.code, scratch: s.scratch });
    },

    lint(id, body) {
      getSession(id);
      return lintCode(body?.code ?? "", "coding");
    },

    async format(body) {
      try {
        return await deps.ruff.format(body?.code ?? "", lintSettings("coding"));
      } catch (err) {
        return { code: null, error: err.message };
      }
    },

    end(id, body) {
      const s = getSession(id);
      if (body && s.paused_at === null && s.status === "active") saveCode(s, body);
      finish(s);
      return { ok: true, id };
    },

    review(id) {
      const s = getSession(id);
      if (s.status !== "finished") {
        throw new ApiError("Reviews (hints, analysis, reference) unlock when the session ends.");
      }
      const data = problemData(s.problem_id);
      return {
        id: s.id,
        problem: data.problem,
        mode: s.mode,
        started_at: s.started_at,
        finished_at: s.finished_at,
        results: results(s),
        pauses: s.pauses,
        submissions: s.submissions ?? [],
        levels: levelSummaries(data),
        hints_html: data.hints_html,
        analysis_html: data.analysis_html,
        reference_code: data.reference_code,
        code: s.code,
        conventions_html: bundle.conventions_html,
      };
    },

    history() {
      const titles = Object.fromEntries(bundle.problems.map((p) => [p.problem.id, p.problem.title]));
      return {
        sessions: [...state.sessions].reverse().map((s) => {
          const res = results(s);
          return {
            id: s.id,
            problem_id: s.problem_id,
            problem_title: titles[s.problem_id] ?? s.problem_id,
            mode: s.mode,
            status: s.status,
            started_at: s.started_at,
            elapsed: res.elapsed,
            timed_levels: res.timed.levels_completed,
            final_levels: res.final.levels_completed,
            pauses: res.pauses,
            current_level: s.current_level,
          };
        }),
      };
    },
  };

  // ---------------------------------------------------------------- system design
  // Kept in state.design so it shares the storage key, and the clock helpers above, with coding.
  function designState() {
    state.design ??= { nextId: 1, sessions: [] };
    return state.design;
  }

  function designData(questionId) {
    const found = bundle.design.questions.find((q) => q.question.id === questionId);
    if (!found) throw new ApiError(`Unknown question '${questionId}'`, 404);
    return found;
  }

  function getDesignSession(id) {
    const s = designState().sessions.find((x) => x.id === id);
    if (!s) throw new ApiError("Session not found.", 404);
    return s;
  }

  const activeDesign = () => [...designState().sessions].reverse().find((s) => s.status === "active") ?? null;

  const designSizes = (data) => [bundle.design.checklist.length, data.key_points.length];

  function designScore(s, [checklistSize, keyPointsSize]) {
    if (!s.assessment) return null;
    const checklist = s.assessment.checklist.filter((i) => i < checklistSize).length;
    const keyPoints = s.assessment.key_points.filter((i) => i < keyPointsSize).length;
    return {
      done: checklist + keyPoints,
      total: checklistSize + keyPointsSize,
      checklist,
      key_points: keyPoints,
    };
  }

  // Time spent on each step against its target, and the overall clock.
  function designResults(s) {
    const starts = Object.entries(s.step_starts).map(([step, t]) => [Number(step), t]);
    const spentTotal = elapsed(s);
    const limit = s.time_limit;
    let targetStart = 0;
    const steps = bundle.design.steps.map(({ step, title, minutes }) => {
      const start = s.step_starts[step] ?? null;
      const later = starts.filter(([m]) => m > step).map(([, t]) => t);
      const end = later.length ? Math.min(...later) : spentTotal;
      const spent = start === null ? null : Math.max(0, end - start);
      const row = {
        step,
        title,
        target: minutes * 60,
        target_start: targetStart,
        started_at: start,
        spent,
        delta: spent === null ? null : spent - minutes * 60,
        overtime: start !== null && start > limit,
      };
      targetStart += minutes * 60;
      return row;
    });
    return {
      time_limit: limit,
      elapsed: spentTotal,
      overtime_seconds: Math.max(0, spentTotal - limit),
      steps,
      steps_reached: starts.length,
      pauses: pauseSummary(s.pauses),
    };
  }

  // Merge notes for known steps and replace the diagram. Refused while paused or finished.
  function saveDesign(s, body) {
    requireEditable(s);
    if (body?.notes != null) {
      const known = new Set(bundle.design.steps.map((st) => String(st.step)));
      for (const [k, v] of Object.entries(body.notes)) if (known.has(k)) s.notes[k] = v;
    }
    if (body?.diagram != null) s.diagram = body.diagram;
  }

  // The session payload carries no hints, key points or reference design.
  function designPayload(s) {
    return {
      id: s.id,
      question: designData(s.question_id).question,
      mode: s.mode,
      status: s.status,
      current_step: s.current_step,
      steps: bundle.design.steps,
      step_starts: s.step_starts,
      notes: s.notes,
      diagram: s.diagram,
      timer: timerState(s),
    };
  }

  const design = {
    listQuestions() {
      const attempts = {};
      const best = {};
      for (const s of designState().sessions) {
        attempts[s.question_id] = (attempts[s.question_id] ?? 0) + 1;
        const data = bundle.design.questions.find((q) => q.question.id === s.question_id);
        const got = data && designScore(s, designSizes(data));
        if (got && (!best[s.question_id] || got.done > best[s.question_id].done)) best[s.question_id] = got;
      }
      return {
        questions: bundle.design.questions.map(({ question }) => ({
          ...question,
          attempts: attempts[question.id] ?? 0,
          best: best[question.id] ?? null,
        })),
        time_limit: bundle.design.time_limit,
        steps: bundle.design.steps,
      };
    },

    framework() {
      const { steps, checklist, time_limit: timeLimit, guide_html: guide, walkthrough_html: walkthrough } = bundle.design;
      return { steps, checklist, time_limit: timeLimit, guide_html: guide, walkthrough_html: walkthrough };
    },

    study(questionId, kind) {
      if (!["hints", "reference"].includes(kind)) throw new ApiError(`Unknown view '${kind}'`, 404);
      const data = designData(questionId);
      const live = activeDesign();
      if (live && live.question_id === questionId) {
        throw new ApiError("This question is in a running session. End the session to open it.");
      }
      const out = { question: data.question, kind, hints: data.hints };
      if (kind === "reference") {
        out.reference_html = data.reference_html;
        out.key_points = data.key_points;
      }
      return out;
    },

    active() {
      const s = activeDesign();
      if (!s) return { session: null };
      return {
        session: {
          id: s.id,
          question: designData(s.question_id).question,
          mode: s.mode,
          current_step: s.current_step,
          timer: timerState(s),
        },
      };
    },

    start({ question_id: questionId, mode, prefer_unseen: preferUnseen = true }) {
      let data;
      if (questionId == null) {
        let pool = bundle.design.questions;
        if (preferUnseen) {
          const seen = new Set(designState().sessions.map((s) => s.question_id));
          const unseen = pool.filter((q) => !seen.has(q.question.id));
          if (unseen.length) pool = unseen;
        }
        data = pick(pool);
      } else {
        data = designData(questionId);
      }
      if (!["strict", "pausable"].includes(mode)) throw new ApiError("Mode must be 'strict' or 'pausable'.", 400);
      if (activeDesign()) {
        throw new ApiError("Finish or end your system design session before starting another.");
      }
      const store = designState();
      const s = {
        id: store.nextId++,
        question_id: data.question.id,
        mode,
        status: "active",
        started_at: clock(),
        time_limit: bundle.design.time_limit,
        paused_at: null,
        total_paused: 0,
        current_step: 1,
        step_starts: { 1: 0 }, // step 1 (requirements) starts with the clock
        notes: Object.fromEntries(bundle.design.steps.map((st) => [String(st.step), st.starter ?? ""])),
        diagram: {},
        assessment: null,
        finished_at: null,
        final_elapsed: null,
        pauses: [],
      };
      store.sessions.push(s);
      return designPayload(s);
    },

    session(id) {
      const s = getDesignSession(id);
      if (s.status !== "active") throw new ApiError("This session has ended; open its review instead.", 410);
      return designPayload(s);
    },

    timer: (id) => timerState(getDesignSession(id)),

    save(id, body) {
      const s = getDesignSession(id);
      saveDesign(s, body);
      return { ok: true, timer: timerState(s) };
    },

    // Steps only go forward; skipping one is allowed.
    step(id, body) {
      const s = getDesignSession(id);
      requireEditable(s);
      const step = body?.step;
      if (!Number.isInteger(step) || !(s.current_step < step && step <= bundle.design.steps.length)) {
        throw new ApiError(`You're on step ${s.current_step}; you can only move forward.`, 400);
      }
      s.step_starts[step] = elapsed(s);
      s.current_step = step;
      return designPayload(s);
    },

    pause(id) {
      const s = getDesignSession(id);
      pause(s);
      return timerState(s);
    },

    resume(id) {
      const s = getDesignSession(id);
      resume(s);
      return timerState(s);
    },

    end(id, body) {
      const s = getDesignSession(id);
      if (body && s.paused_at === null && s.status === "active") saveDesign(s, body);
      finish(s);
      return { ok: true, id };
    },

    review(id) {
      const s = getDesignSession(id);
      if (s.status !== "finished") {
        throw new ApiError("The review (reference design, self-check) opens when the session ends.");
      }
      const data = designData(s.question_id);
      return {
        id: s.id,
        question: data.question,
        hints: data.hints,
        mode: s.mode,
        started_at: s.started_at,
        finished_at: s.finished_at,
        results: designResults(s),
        pauses: s.pauses,
        steps: bundle.design.steps,
        notes: s.notes,
        diagram: s.diagram,
        checklist: bundle.design.checklist,
        key_points: data.key_points,
        assessment: s.assessment,
        score: designScore(s, designSizes(data)),
        reference_html: data.reference_html,
      };
    },

    // Which checklist items and key points you ticked (indices). Only after the session.
    assess(id, body) {
      const s = getDesignSession(id);
      if (s.status !== "finished") throw new ApiError("Self-review opens when the session ends.");
      const sizes = designSizes(designData(s.question_id));
      const picked = { checklist: body?.checklist ?? [], key_points: body?.key_points ?? [] };
      Object.keys(picked).forEach((name, n) => {
        const items = picked[name];
        if (!Array.isArray(items) || items.some((i) => !Number.isInteger(i) || i < 0 || i >= sizes[n])) {
          throw new ApiError(`${name}: item index out of range.`, 400);
        }
        picked[name] = [...new Set(items)].sort((a, b) => a - b);
      });
      s.assessment = picked;
      return { assessment: picked, score: designScore(s, sizes) };
    },

    history() {
      const stepCount = bundle.design.steps.length;
      return {
        sessions: [...designState().sessions].reverse().map((s) => {
          const data = bundle.design.questions.find((q) => q.question.id === s.question_id);
          const res = designResults(s);
          return {
            id: s.id,
            question_id: s.question_id,
            question_title: data ? data.question.title : s.question_id,
            mode: s.mode,
            status: s.status,
            started_at: s.started_at,
            elapsed: res.elapsed,
            time_limit: res.time_limit,
            steps_reached: res.steps_reached,
            step_count: stepCount,
            pauses: res.pauses,
            score: data ? designScore(s, designSizes(data)) : null,
          };
        }),
      };
    },
  };

  // ---------------------------------------------------------------- algorithms
  // Kept in state.algo. Run checks the examples; Submit adds the hidden tests, and the first
  // submit that passes them all marks the problem solved (solved_at, in elapsed seconds).
  function algoState() {
    state.algo ??= { nextId: 1, sessions: [] };
    return state.algo;
  }

  function algoData(problemId) {
    const found = bundle.algo.problems.find((p) => p.problem.id === problemId);
    if (!found) throw new ApiError(`Unknown problem '${problemId}'`, 404);
    return found;
  }

  function getAlgoSession(id) {
    const s = algoState().sessions.find((x) => x.id === id);
    if (!s) throw new ApiError("Session not found.", 404);
    return s;
  }

  const activeAlgo = () => [...algoState().sessions].reverse().find((s) => s.status === "active") ?? null;

  // What the solver sees: the statement and the examples (the shown tests).
  const algoQuestion = (data) => ({
    statement_html: data.statement_html,
    params: data.params,
    examples: data.examples,
  });

  function algoPayload(s) {
    const data = algoData(s.problem_id);
    return {
      id: s.id,
      problem: data.problem,
      mode: s.mode,
      status: s.status,
      ...algoQuestion(data),
      code: s.code,
      scratch: s.scratch,
      solved_at: s.solved_at ?? null,
      timer: timerState(s),
    };
  }

  const passedCount = (sub) => sub.shown_passed + sub.hidden_passed;

  // The submit that passed the most tests (the earliest of equals), optionally by a time.
  function bestSubmit(submits, before) {
    const pool = submits.filter((x) => before == null || x.elapsed <= before);
    if (!pool.length) return null;
    const best = pool.reduce((a, b) => (passedCount(b) > passedCount(a) || (passedCount(b) === passedCount(a) && b.elapsed < a.elapsed) ? b : a));
    return {
      passed: passedCount(best),
      total: best.shown_total + best.hidden_total,
      elapsed: best.elapsed,
      too_slow: best.too_slow,
    };
  }

  // The timed result (by the limit) and the final one (including overtime).
  function algoResults(s) {
    const limit = s.time_limit;
    const subs = s.submissions ?? [];
    const submits = subs.filter((x) => x.kind === "submit");
    const solvedAt = s.solved_at ?? null;
    const spent = elapsed(s);
    return {
      time_limit: limit,
      elapsed: spent,
      overtime_seconds: Math.max(0, spent - limit),
      solved_at: solvedAt,
      timed: { solved: solvedAt !== null && solvedAt <= limit, best: bestSubmit(submits, limit) },
      final: { solved: solvedAt !== null, best: bestSubmit(submits, null) },
      pauses: pauseSummary(s.pauses),
      runs: subs.length - submits.length,
      submits: submits.length,
    };
  }

  // Full detail for the shown tests; counts only for the hidden ones.
  function summarizeAlgo(tests, run) {
    const shown = [];
    const counts = { shown_passed: 0, shown_total: 0, hidden_passed: 0, hidden_total: 0, too_slow: 0 };
    let allPassed = run.import_error === null && run.crashed === null;
    for (const test of tests) {
      const result = run.results[test.id] ?? null;
      const passed = Boolean(result?.passed);
      allPassed &&= passed;
      counts[`${test.visibility}_total`] += 1;
      counts[`${test.visibility}_passed`] += passed ? 1 : 0;
      counts.too_slow += tooSlow(result) ? 1 : 0;
      if (test.visibility === "shown") {
        const step = result?.steps?.[0] ?? {};
        shown.push({
          id: test.id,
          name: test.name,
          passed,
          ran: result !== null,
          actual: step.actual ?? null,
          error: result?.error ?? null,
          stdout: result?.stdout ?? "",
          ms: result?.ms ?? null,
        });
      }
    }
    return { shown, counts, allPassed };
  }

  const algo = {
    listProblems() {
      const stats = {};
      for (const s of algoState().sessions) {
        const st = (stats[s.problem_id] ??= { attempts: 0, solved: false, solved_in_time: false, best_time: null });
        st.attempts += 1;
        if (s.solved_at != null) {
          st.solved = true;
          st.solved_in_time ||= s.solved_at <= s.time_limit;
          if (st.best_time === null || s.solved_at < st.best_time) st.best_time = s.solved_at;
        }
      }
      const empty = { attempts: 0, solved: false, solved_in_time: false, best_time: null };
      return {
        problems: bundle.algo.problems.map(({ problem }) => ({ ...problem, ...(stats[problem.id] ?? empty) })),
        minutes: bundle.algo.minutes,
        patterns: bundle.algo.patterns,
      };
    },

    study(problemId, kind) {
      if (!["question", "hints", "solution"].includes(kind)) throw new ApiError(`Unknown view '${kind}'`, 404);
      const data = algoData(problemId);
      const live = activeAlgo();
      if (live && live.problem_id === problemId) {
        throw new ApiError("This problem is in a running session. End the session to open it.");
      }
      const out = { problem: data.problem, kind };
      if (kind === "question") return { ...out, ...algoQuestion(data) };
      out.foundations = data.foundations;
      out.hints_html = data.hints_html;
      if (kind === "solution") out.explanation_html = data.explanation_html;
      return out;
    },

    active() {
      const s = activeAlgo();
      if (!s) return { session: null };
      return {
        session: {
          id: s.id,
          problem: algoData(s.problem_id).problem,
          mode: s.mode,
          solved_at: s.solved_at ?? null,
          timer: timerState(s),
        },
      };
    },

    start({ problem_id: problemId, mode, prefer_unseen: preferUnseen = true, difficulty = null, pattern = null }) {
      if (!bundle.algo.problems.length) throw new ApiError("No algorithm problems are built. Run tools/build_algo.py.", 500);
      let data;
      if (problemId == null) {
        let pool = bundle.algo.problems.filter(({ problem }) => (difficulty == null || problem.difficulty === difficulty)
          && (pattern == null || problem.patterns.includes(pattern)));
        if (!pool.length) throw new ApiError("No problem matches those filters.", 400);
        if (preferUnseen) {
          const seen = new Set(algoState().sessions.map((s) => s.problem_id));
          const unseen = pool.filter((p) => !seen.has(p.problem.id));
          if (unseen.length) pool = unseen;
        }
        data = pick(pool);
      } else {
        data = algoData(problemId);
      }
      if (!["strict", "pausable"].includes(mode)) throw new ApiError("Mode must be 'strict' or 'pausable'.", 400);
      if (activeAlgo()) throw new ApiError("Finish or end your algorithms session before starting another.");
      const store = algoState();
      const s = {
        id: store.nextId++,
        problem_id: data.problem.id,
        mode,
        status: "active",
        started_at: clock(),
        time_limit: data.problem.minutes * 60,
        paused_at: null,
        total_paused: 0,
        code: data.starter_code,
        scratch: data.scratch_starter,
        solved_at: null,
        finished_at: null,
        final_elapsed: null,
        pauses: [],
        submissions: [],
      };
      store.sessions.push(s);
      return algoPayload(s);
    },

    session(id) {
      const s = getAlgoSession(id);
      if (s.status !== "active") throw new ApiError("This session has ended; open its review instead.", 410);
      return algoPayload(s);
    },

    timer: (id) => timerState(getAlgoSession(id)),

    save(id, body) {
      const s = getAlgoSession(id);
      saveCode(s, body);
      return { ok: true, timer: timerState(s) };
    },

    pause(id) {
      const s = getAlgoSession(id);
      pause(s);
      return timerState(s);
    },

    resume(id) {
      const s = getAlgoSession(id);
      resume(s);
      return timerState(s);
    },

    async execute(id, kind, body) {
      let s = getAlgoSession(id);
      saveCode(s, body);
      persist();
      const { code, problem_id: problemId } = s;
      const file = await testsFile("algo", problemId);
      const tests = file.tests.filter((t) => kind === "submit" || t.visibility === "shown");
      const run = await deps.python.runTests({ code, className: file.class_name, tests, options: file.options });
      const lint = await lintCode(code, "algo");
      const { shown, counts, allPassed } = summarizeAlgo(tests, run);

      readState(); // the run took a while: build on what's stored now
      s = getAlgoSession(id);
      const spent = elapsed(s);
      (s.submissions ??= []).push({
        kind, elapsed: spent, at: clock(), all_passed: allPassed, ...counts, lint_count: lint.issues.length,
      });
      let solved = false;
      if (kind === "submit" && allPassed && (s.solved_at ?? null) === null) {
        s.solved_at = spent;
        solved = true;
      }
      persist();
      return {
        kind,
        all_passed: allPassed,
        import_error: run.import_error,
        import_stdout: run.import_stdout,
        crashed: run.crashed,
        timed_out: run.timed_out,
        stopped: run.stopped, // a test hit its time limit; the tests after it didn't run
        ms: run.ms,
        shown,
        counts, // hidden tests: counts only, never inputs or outputs
        lint,
        solved, // this submit solved it for the first time
        solved_at: s.solved_at ?? null,
        timer: timerState(s),
      };
    },

    run: (id, body) => algo.execute(id, "run", body),
    submit: (id, body) => algo.execute(id, "submit", body),

    async scratch(id, body) {
      const s = getAlgoSession(id);
      saveCode(s, body);
      persist();
      const { code, scratch } = s;
      return deps.python.runScratch({ code, scratch, files: { "helpers.py": await helpers() } });
    },

    lint(id, body) {
      getAlgoSession(id);
      return lintCode(body?.code ?? "", "algo");
    },

    end(id, body) {
      const s = getAlgoSession(id);
      if (body && s.paused_at === null && s.status === "active") saveCode(s, body);
      finish(s);
      return { ok: true, id };
    },

    review(id) {
      const s = getAlgoSession(id);
      if (s.status !== "finished") throw new ApiError("The review (hints, explanation, solution) opens when it ends.");
      const data = algoData(s.problem_id);
      return {
        id: s.id,
        problem: data.problem,
        mode: s.mode,
        started_at: s.started_at,
        finished_at: s.finished_at,
        results: algoResults(s),
        pauses: s.pauses,
        submissions: s.submissions ?? [],
        ...algoQuestion(data),
        hints_html: data.hints_html,
        explanation_html: data.explanation_html,
        foundations: data.foundations,
        code: s.code,
      };
    },

    history() {
      return {
        sessions: [...algoState().sessions].reverse().map((s) => {
          const data = bundle.algo.problems.find((p) => p.problem.id === s.problem_id);
          const res = algoResults(s);
          return {
            id: s.id,
            problem_id: s.problem_id,
            problem_title: data ? data.problem.title : s.problem_id,
            difficulty: data ? data.problem.difficulty : null,
            mode: s.mode,
            status: s.status,
            started_at: s.started_at,
            elapsed: res.elapsed,
            time_limit: res.time_limit,
            solved_at: res.solved_at,
            timed: res.timed,
            final: res.final,
            pauses: res.pauses,
          };
        }),
      };
    },
  };

  // ---------------------------------------------------------------- foundations and tech
  // Every page is pre-rendered into data.json; the track is the first captured group.
  function foundations(track) {
    return bundle.foundations?.[track] ?? { cards: [], pages: {} };
  }

  const learn = {
    list: (track) => ({ pages: foundations(track).cards }),
    page(track, slug) {
      const page = foundations(track).pages[slug];
      if (!page) throw new ApiError(`Unknown page '${slug}'`, 404);
      return page;
    },
    // A tech investigation's project, for the file browser.
    files(track, slug) {
      const project = foundations(track).projects?.[slug];
      if (!project) throw new ApiError(`Page '${slug}' has no project folder`, 404);
      return project;
    },
  };

  // ---------------------------------------------------------------- history export and import
  // History lives in this browser only, so it can be saved to a file and loaded elsewhere (another
  // browser, or the site at another address). tools/export_history.py writes the same format.
  const TRACKS = {
    coding: { list: () => state, key: "problem_id" },
    algo: { list: algoState, key: "problem_id" },
    design: { list: designState, key: "question_id" },
  };

  const backup = {
    export() {
      const out = { format: BACKUP_FORMAT, version: 1, exported_at: clock() };
      for (const [track, { list }] of Object.entries(TRACKS)) out[track] = { sessions: list().sessions };
      return out;
    },

    // Adds the file's sessions to this browser's history, skipping ones it already has (same
    // question, same start time). Imported sessions get new ids.
    import(body) {
      if (body?.format !== BACKUP_FORMAT || !Number.isInteger(body.version)) {
        throw new ApiError("That file isn't a history export from this app.", 400);
      }
      if (body.version > 1) throw new ApiError("That export is from a newer version of the app.", 400);
      const added = {};
      for (const [track, { list, key }] of Object.entries(TRACKS)) {
        const store = list();
        const incoming = body[track]?.sessions ?? [];
        if (!Array.isArray(incoming)) throw new ApiError(`${track}: sessions must be a list.`, 400);
        const have = new Set(store.sessions.map((s) => `${s[key]}@${s.started_at}`));
        let count = 0;
        for (const raw of incoming) {
          if (!raw || typeof raw[key] !== "string" || typeof raw.started_at !== "number") {
            throw new ApiError(`${track}: a session is missing its ${key} or started_at.`, 400);
          }
          if (have.has(`${raw[key]}@${raw.started_at}`)) continue;
          const s = structuredClone(raw);
          s.id = store.nextId++;
          // Only one session per track can be running: if this browser has one, an imported
          // running session ends, where it was paused or else now.
          if (s.status === "active" && store.sessions.some((x) => x.status === "active")) {
            if (s.paused_at === null) s.paused_at = clock();
            s.final_elapsed = elapsed({ ...s, status: "active" }, s.paused_at);
            s.finished_at = s.paused_at;
            s.status = "finished";
          }
          store.sessions.push(s);
          have.add(`${raw[key]}@${raw.started_at}`);
          count += 1;
        }
        store.sessions.sort((a, b) => a.started_at - b.started_at);
        added[track] = count;
      }
      return { ok: true, added };
    },
  };

  // ---------------------------------------------------------------- routes
  // [method, path pattern, handler]; captured groups are passed first (ids as numbers).
  const E = endpoints;
  const D = design;
  const A = algo;
  const ROUTES = [
    ["GET", /^\/api\/problems$/, E.listProblems],
    ["GET", /^\/api\/problems\/([\w-]+)\/([\w-]+)$/, E.study],
    ["GET", /^\/api\/active$/, E.active],
    ["POST", /^\/api\/sessions$/, E.start],
    ["GET", /^\/api\/sessions\/(\d+)$/, E.session],
    ["GET", /^\/api\/sessions\/(\d+)\/timer$/, E.timer],
    ["PUT", /^\/api\/sessions\/(\d+)\/code$/, E.save],
    ["POST", /^\/api\/sessions\/(\d+)\/pause$/, E.pause],
    ["POST", /^\/api\/sessions\/(\d+)\/resume$/, E.resume],
    ["POST", /^\/api\/sessions\/(\d+)\/run$/, E.run],
    ["POST", /^\/api\/sessions\/(\d+)\/submit$/, E.submit],
    ["POST", /^\/api\/sessions\/(\d+)\/scratch$/, E.scratch],
    ["POST", /^\/api\/sessions\/(\d+)\/lint$/, E.lint],
    ["POST", /^\/api\/format$/, E.format],
    ["POST", /^\/api\/sessions\/(\d+)\/end$/, E.end],
    ["GET", /^\/api\/sessions\/(\d+)\/review$/, E.review],
    ["GET", /^\/api\/history$/, E.history],
    ["GET", /^\/api\/backup$/, backup.export],
    ["POST", /^\/api\/backup$/, backup.import],
    ["GET", /^\/api\/design\/questions$/, D.listQuestions],
    ["GET", /^\/api\/design\/framework$/, D.framework],
    ["GET", /^\/api\/design\/questions\/([\w-]+)\/([\w-]+)$/, D.study],
    ["GET", /^\/api\/design\/active$/, D.active],
    ["POST", /^\/api\/design\/sessions$/, D.start],
    ["GET", /^\/api\/design\/sessions\/(\d+)$/, D.session],
    ["GET", /^\/api\/design\/sessions\/(\d+)\/timer$/, D.timer],
    ["PUT", /^\/api\/design\/sessions\/(\d+)\/notes$/, D.save],
    ["POST", /^\/api\/design\/sessions\/(\d+)\/step$/, D.step],
    ["POST", /^\/api\/design\/sessions\/(\d+)\/pause$/, D.pause],
    ["POST", /^\/api\/design\/sessions\/(\d+)\/resume$/, D.resume],
    ["POST", /^\/api\/design\/sessions\/(\d+)\/end$/, D.end],
    ["GET", /^\/api\/design\/sessions\/(\d+)\/review$/, D.review],
    ["PUT", /^\/api\/design\/sessions\/(\d+)\/assessment$/, D.assess],
    ["GET", /^\/api\/design\/history$/, D.history],
    ["GET", /^\/api\/algo\/problems$/, A.listProblems],
    ["GET", /^\/api\/algo\/problems\/([\w-]+)\/([\w-]+)$/, A.study],
    ["GET", /^\/api\/algo\/active$/, A.active],
    ["POST", /^\/api\/algo\/sessions$/, A.start],
    ["GET", /^\/api\/algo\/sessions\/(\d+)$/, A.session],
    ["GET", /^\/api\/algo\/sessions\/(\d+)\/timer$/, A.timer],
    ["PUT", /^\/api\/algo\/sessions\/(\d+)\/code$/, A.save],
    ["POST", /^\/api\/algo\/sessions\/(\d+)\/pause$/, A.pause],
    ["POST", /^\/api\/algo\/sessions\/(\d+)\/resume$/, A.resume],
    ["POST", /^\/api\/algo\/sessions\/(\d+)\/run$/, A.run],
    ["POST", /^\/api\/algo\/sessions\/(\d+)\/submit$/, A.submit],
    ["POST", /^\/api\/algo\/sessions\/(\d+)\/scratch$/, A.scratch],
    ["POST", /^\/api\/algo\/sessions\/(\d+)\/lint$/, A.lint],
    ["POST", /^\/api\/algo\/sessions\/(\d+)\/end$/, A.end],
    ["GET", /^\/api\/algo\/sessions\/(\d+)\/review$/, A.review],
    ["GET", /^\/api\/algo\/history$/, A.history],
    ["GET", /^\/api\/(design|algo)\/foundations$/, learn.list],
    ["GET", /^\/api\/(design|algo)\/foundations\/([\w-]+)$/, learn.page],
    ["GET", /^\/api\/(tech)\/pages$/, learn.list],
    ["GET", /^\/api\/(tech)\/pages\/([\w-]+)$/, learn.page],
    ["GET", /^\/api\/(tech)\/pages\/([\w-]+)\/files$/, learn.files],
  ];
  // Routes whose first captured group is a session id.
  const ID_ROUTES = new Set([
    E.session, E.timer, E.save, E.pause, E.resume, E.run, E.submit, E.scratch, E.lint, E.end, E.review,
    D.session, D.timer, D.save, D.step, D.pause, D.resume, D.end, D.review, D.assess,
    A.session, A.timer, A.save, A.pause, A.resume, A.run, A.submit, A.scratch, A.lint, A.end, A.review,
  ]);

  async function handle(method, path, body) {
    await loadBundle();
    for (const [m, pattern, fn] of ROUTES) {
      const match = m === method && path.split("?")[0].match(pattern);
      if (!match) continue;
      readState();
      const args = match.slice(1);
      if (ID_ROUTES.has(fn)) args[0] = Number(args[0]);
      const out = fn(...args, body);
      // Handlers that run code are async and store their own changes, before and after the run.
      if (out instanceof Promise) return structuredClone(await out);
      if (method !== "GET") persist();
      return structuredClone(out);
    }
    throw new ApiError(`Not found: ${method} ${path}`, 404);
  }

  return { handle };
}

let backend = null;

// The app's backend (common.js api() calls this).
export function handle(method, path, body) {
  backend ??= createBackend(browserDeps());
  return backend.handle(method, path, body);
}

// Start loading Python and ruff, so the first Run or lint doesn't wait for them (session pages).
export function warmUp() {
  python.warmUp().catch(() => { /* reported when a run needs it */ });
  ruff.warmUp().catch(() => { /* reported by lint */ });
}

export const coolDown = python.coolDown;
