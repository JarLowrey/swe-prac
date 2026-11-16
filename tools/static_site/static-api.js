// Browser-side stand-in for the FastAPI backend, used on the static site (GitHub Pages).
//
// app.js sends every request through api(); when this file has defined window.SWE_STATIC, that
// call lands in handle() below instead of the network. Responses have the same shape as the real
// API's. Sessions live in localStorage and mirror swe_prac/sessions.py (timer, pausing, scoring).
//
// Nothing here can run Python, so run / submit / scratch / format are refused and lint reports
// that it is unavailable. app.js disables those buttons, so no level can be passed on this site.
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
    const now = clock();
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
      pauses: {
        count: s.pauses.length,
        total_seconds: s.pauses.reduce((sum, p) => sum + (p.ended_at ?? now) - p.started_at, 0),
      },
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

  // [method, path pattern, handler]; captured groups are passed first (ids as numbers).
  const E = endpoints;
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
  ];
  const ID_ROUTES = new Set([E.session, E.timer, E.save, E.pause, E.resume, E.end, E.review]);

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
