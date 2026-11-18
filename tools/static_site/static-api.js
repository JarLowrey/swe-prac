// Browser-side stand-in for the FastAPI backend, used on the static site (GitHub Pages).
//
// The frontend sends every request through api() (common.js); when this file has defined
// window.SWE_STATIC, that call lands in handle() below instead of the network. Responses have the
// same shape as the real API's. Sessions live in localStorage and mirror swe_prac/sessions.py
// (timer, pausing, scoring), swe_prac/design_sessions.py (system design) and
// swe_prac/algo_sessions.py (algorithms).
//
// Nothing here can run Python, so run / submit / scratch / format are refused and lint reports
// that it is unavailable. app.js and algo.js disable those buttons, so no level can be passed and
// no algorithm problem solved on this site. System design needs no code execution, so that whole
// section works here, and so do the foundations pages of both tracks.
(() => {
  const STORAGE_KEY = "swe-prac-static-v1";
  const NEEDS_SERVER = "Running code needs the local server. It isn't available on the static site.";

  class ApiError extends Error {
    constructor(message, status = 409) {
      super(message);
      this.status = status;
    }
  }

  // ---------------------------------------------------------------- data
  let bundle = null; // data.json, written by tools/build_static.py

  async function loadBundle() {
    const res = await fetch(new URL("data.json", document.baseURI));
    if (!res.ok) throw new ApiError(`Could not load data.json (${res.status})`, 500);
    bundle = await res.json();
  }

  function problemData(problemId) {
    const found = bundle.problems.find((p) => p.problem.id === problemId);
    if (!found) throw new ApiError(`Unknown problem '${problemId}'`, 404);
    return found;
  }

  // ---------------------------------------------------------------- storage
  let state = { nextId: 1, sessions: [] };

  // Re-read on every request so two open tabs don't overwrite each other. If storage is
  // unavailable (private mode), the in-memory copy carries on for this page load.
  function readState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) state = JSON.parse(raw);
    } catch { /* keep the in-memory state */ }
  }

  function persist() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* not persisted */ }
  }

  const clock = () => Date.now() / 1000;

  function getSession(id) {
    const s = state.sessions.find((x) => x.id === id);
    if (!s) throw new ApiError("Session not found.", 404);
    return s;
  }

  const activeSession = () => [...state.sessions].reverse().find((s) => s.status === "active") ?? null;

  // ---------------------------------------------------------------- timer (sessions.py)
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

  // ---------------------------------------------------------------- results (sessions.results)
  // A static session can't submit code, so completions and submissions stay empty. The shape is
  // kept anyway so the review and history pages render exactly as they do with the server.
  function results(s) {
    const limit = s.time_limit;
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
    const spent = elapsed(s);
    return {
      time_limit: limit,
      elapsed: spent,
      overtime_seconds: Math.max(0, spent - limit),
      timed: {
        levels_completed: timedLevels,
        stopped_level: timedLevels < total ? timedLevels + 1 : null,
        stopped_level_ratio: null,
      },
      final: {
        levels_completed: finalLevels,
        stopped_level: finalLevels < total ? finalLevels + 1 : null,
        stopped_level_ratio: null,
      },
      levels,
      pauses: pauseSummary(s.pauses),
      runs: 0,
      submits: 0,
    };
  }

  // ---------------------------------------------------------------- endpoints (app.py)
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
      if (!["strict", "pausable"].includes(mode)) throw new ApiError("Mode must be 'strict' or 'pausable'.", 400);
      let data;
      if (problemId == null) {
        let pool = bundle.problems;
        if (preferUnseen) {
          const seen = new Set(state.sessions.map((s) => s.problem_id));
          const unseen = pool.filter((p) => !seen.has(p.problem.id));
          if (unseen.length) pool = unseen;
        }
        data = pool[Math.floor(Math.random() * pool.length)];
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
        submissions: [],
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

    // Needs Python (and ruff), so there is no browser equivalent.
    lint: () => ({ issues: [], error: "Linting needs the local server (ruff). It isn't available on the static site." }),
    needsServer() { throw new ApiError(NEEDS_SERVER, 501); },
  };

  // ---------------------------------------------------------------- system design (design_api.py)
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
      const { steps, checklist, time_limit, guide_html, walkthrough_html } = bundle.design;
      return { steps, checklist, time_limit, guide_html, walkthrough_html };
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
        data = pool[Math.floor(Math.random() * pool.length)];
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

  // ---------------------------------------------------------------- algorithms (algo_api.py)
  // Kept in state.algo. Without code execution there are no runs or submits, so a session is
  // never solved; the shapes still match the server's so the pages render the same.
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
      solved_at: null,
      timer: timerState(s),
    };
  }

  // algo_sessions.results for a session with no submits: not solved, no best attempt.
  function algoResults(s) {
    const spent = elapsed(s);
    return {
      time_limit: s.time_limit,
      elapsed: spent,
      overtime_seconds: Math.max(0, spent - s.time_limit),
      solved_at: null,
      timed: { solved: false, best: null },
      final: { solved: false, best: null },
      pauses: pauseSummary(s.pauses),
      runs: 0,
      submits: 0,
    };
  }

  const algo = {
    listProblems() {
      const attempts = {};
      for (const s of algoState().sessions) attempts[s.problem_id] = (attempts[s.problem_id] ?? 0) + 1;
      return {
        problems: bundle.algo.problems.map(({ problem }) => ({
          ...problem,
          attempts: attempts[problem.id] ?? 0,
          solved: false,
          solved_in_time: false,
          best_time: null,
        })),
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
          solved_at: null,
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
        data = pool[Math.floor(Math.random() * pool.length)];
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
        finished_at: null,
        final_elapsed: null,
        pauses: [],
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
        submissions: [],
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
            solved_at: null,
            timed: res.timed,
            final: res.final,
            pauses: res.pauses,
          };
        }),
      };
    },
  };

  // ---------------------------------------------------------------- foundations (pages.py)
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
  };

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
    ["POST", /^\/api\/sessions\/(\d+)\/end$/, E.end],
    ["GET", /^\/api\/sessions\/(\d+)\/review$/, E.review],
    ["GET", /^\/api\/history$/, E.history],
    ["POST", /^\/api\/sessions\/(\d+)\/lint$/, E.lint],
    ["POST", /^\/api\/sessions\/(\d+)\/(run|submit|scratch)$/, E.needsServer],
    ["POST", /^\/api\/format$/, E.needsServer],
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
    ["POST", /^\/api\/algo\/sessions\/(\d+)\/end$/, A.end],
    ["GET", /^\/api\/algo\/sessions\/(\d+)\/review$/, A.review],
    ["GET", /^\/api\/algo\/history$/, A.history],
    ["POST", /^\/api\/algo\/sessions\/(\d+)\/lint$/, E.lint],
    ["POST", /^\/api\/algo\/sessions\/(\d+)\/(run|submit|scratch)$/, E.needsServer],
    ["GET", /^\/api\/(design|algo)\/foundations$/, learn.list],
    ["GET", /^\/api\/(design|algo)\/foundations\/([\w-]+)$/, learn.page],
  ];
  const ID_ROUTES = new Set([
    E.session, E.timer, E.save, E.pause, E.resume, E.end, E.review,
    D.session, D.timer, D.save, D.step, D.pause, D.resume, D.end, D.review, D.assess,
    A.session, A.timer, A.save, A.pause, A.resume, A.end, A.review,
  ]);

  async function handle(method, path, body) {
    if (!bundle) await loadBundle(); // after the first call everything below runs synchronously
    for (const [m, pattern, fn] of ROUTES) {
      const match = m === method && path.split("?")[0].match(pattern);
      if (!match) continue;
      readState();
      const args = match.slice(1);
      if (ID_ROUTES.has(fn)) args[0] = Number(args[0]);
      const out = fn(...args, body);
      if (method !== "GET") persist();
      return structuredClone(out);
    }
    throw new ApiError(`Not found: ${method} ${path}`, 404);
  }

  window.SWE_STATIC = { handle, needsServer: NEEDS_SERVER };
})();
