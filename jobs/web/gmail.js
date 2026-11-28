// Gmail, straight from the browser: Google's sign-in library for a read-only access token, then
// the Gmail REST API. No server: the token goes from Google to this page, lives only in memory
// (an hour at most) and is never stored. Each visitor uses an OAuth client ID from their own
// Google Cloud project (the Connect Gmail page explains how to make one).
//
// Downloading is paced. Gmail charges 60 quota units for each message fetched in full, out of
// 6,000 a minute per user, so about 100 messages a minute is the ceiling; sync() stays under it,
// waits when Gmail says to slow down, and skips messages already in the browser.

export const SCOPE = "https://www.googleapis.com/auth/gmail.readonly";
const API = "https://gmail.googleapis.com/gmail/v1/users/me";
const GIS_SRC = "https://accounts.google.com/gsi/client";

export class AuthError extends Error {}

// ---------------------------------------------------------------- sign-in (browser only)
let gis = null;
let tokenClient = null;
let tokenClientId = "";
let token = null; // { access_token, expires_at }
let waiting = null; // the connect() call a token response settles

export function loadGis() {
  gis ??= new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = GIS_SRC;
    s.async = true;
    s.onload = () => resolve(window.google);
    s.onerror = () => {
      gis = null;
      reject(new Error("Couldn't load Google's sign-in script. Check your connection, or allow accounts.google.com if a blocker stops it."));
    };
    document.head.appendChild(s);
  });
  return gis;
}

// Load the sign-in script and set up the client ahead of time, so the click that connects can
// open Google's popup straight away (browsers block popups opened long after a click).
export async function prepare(clientId) {
  const google = await loadGis();
  if (tokenClient && tokenClientId === clientId) return;
  tokenClientId = clientId;
  tokenClient = google.accounts.oauth2.initTokenClient({
    client_id: clientId,
    scope: SCOPE,
    callback: (resp) => {
      const w = waiting;
      waiting = null;
      if (!w) return;
      if (resp.error) return w.reject(new Error(resp.error_description || resp.error));
      if (!google.accounts.oauth2.hasGrantedAllScopes(resp, SCOPE)) {
        return w.reject(new Error("Google didn't grant read access to Gmail. Connect again and tick “View your email messages and settings”."));
      }
      token = { access_token: resp.access_token, expires_at: Date.now() + Number(resp.expires_in || 3600) * 1000 };
      w.resolve(token.access_token);
    },
    error_callback: (err) => {
      const w = waiting;
      waiting = null;
      const why = { popup_closed: "The Google window was closed before access was granted.",
        popup_failed_to_open: "The browser blocked Google's sign-in window. Allow popups for this site and try again." }[err?.type];
      w?.reject(new Error(why || `Google sign-in failed (${err?.type || "unknown"}).`));
    },
  });
}

// A token that's good for at least another minute, or null.
export const currentToken = () => (token && Date.now() < token.expires_at - 60_000 ? token.access_token : null);

// Call from a click. `hint` is the address last used, so Google can skip the account chooser.
export function connect(hint = "") {
  if (!tokenClient) return Promise.reject(new Error("Google sign-in isn't ready yet. Try again in a moment."));
  if (currentToken()) return Promise.resolve(currentToken());
  return new Promise((resolve, reject) => {
    waiting?.reject(new Error("Replaced by a newer sign-in."));
    waiting = { resolve, reject };
    tokenClient.requestAccessToken({ prompt: "", ...(hint ? { login_hint: hint } : {}) });
  });
}

// Drop a token Gmail refused, so the next connect() asks Google for a new one.
export function forget() { token = null; }

export function disconnect() {
  const t = token;
  token = null;
  if (t && window.google?.accounts?.oauth2) window.google.accounts.oauth2.revoke(t.access_token, () => {});
}

// ---------------------------------------------------------------- the REST calls
const realSleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Downloads every message matching `query` that isn't in `known` (a Set of ids), in batches.
//   onBatch(apiMessages, account)  awaited for each batch of up to `batchSize` (parse and store them)
//   onProgress({phase, listed, todo, done, failed, waitingUntil})
// Returns {account, listed, fetched, failed: [ids], stopped}. Throws AuthError when the token is
// refused (expired or revoked): what was downloaded before that is already handed to onBatch.
export async function sync({
  accessToken, query, known = new Set(), onBatch, onProgress = () => {}, signal,
  fetchImpl = (...a) => fetch(...a), sleep = realSleep, now = () => Date.now(),
  perMinute = 90, concurrency = 3, batchSize = 25,
}) {
  const state = { phase: "listing", listed: 0, todo: 0, done: 0, failed: 0, waitingUntil: 0 };
  const report = () => onProgress({ ...state });
  const gap = 60_000 / perMinute;
  let nextStart = now();
  let pausedUntil = 0;

  // One request at a time through the pacer; retries rate limits and server errors.
  async function call(path, cost = 1) {
    for (let attempt = 0; ; attempt++) {
      if (signal?.aborted) throw new DOMException("Stopped", "AbortError");
      const t = now();
      const start = Math.max(t, nextStart, pausedUntil);
      nextStart = start + gap * cost;
      if (start > t) await sleep(start - t);
      let res;
      try {
        res = await fetchImpl(`${API}/${path}`, { headers: { Authorization: `Bearer ${accessToken}` }, signal });
      } catch (err) {
        if (err?.name === "AbortError" || attempt >= 3) throw err;
        await sleep(2000 * 2 ** attempt);
        continue;
      }
      if (res.ok) return res.json();
      if (res.status === 401) throw new AuthError("Gmail access has expired. Connect again to carry on.");
      const body = await res.json().catch(() => ({}));
      const reason = body?.error?.errors?.[0]?.reason || body?.error?.status || "";
      const limited = res.status === 429 || (res.status === 403 && /rate|quota/i.test(reason));
      if (res.status === 404) return null; // deleted since it was listed
      if ((limited || res.status >= 500) && attempt < 5) {
        const after = Number(res.headers?.get?.("Retry-After")) * 1000;
        const wait = after > 0 ? after : Math.min(120_000, 15_000 * 2 ** attempt);
        pausedUntil = now() + wait;
        state.waitingUntil = pausedUntil;
        report();
        continue;
      }
      if (res.status === 403) {
        throw new AuthError(body?.error?.message || "Gmail refused access. Check that the Gmail API is enabled in your Google Cloud project.");
      }
      throw new Error(`Gmail answered ${res.status}${body?.error?.message ? `: ${body.error.message}` : ""}`);
    }
  }

  const profile = await call("profile");
  const account = profile?.emailAddress || "";
  report();

  // messages.list: ids only, 500 a page (5 units a page, so cheap next to the downloads)
  const ids = [];
  let pageToken = "";
  do {
    const q = new URLSearchParams({ q: query, maxResults: "500", fields: "messages(id),nextPageToken" });
    if (pageToken) q.set("pageToken", pageToken);
    const page = await call(`messages?${q}`, 5 / 60);
    for (const m of page?.messages ?? []) ids.push(m.id);
    pageToken = page?.nextPageToken || "";
    state.listed = ids.length;
    report();
  } while (pageToken);

  const todo = ids.filter((id) => !known.has(id));
  Object.assign(state, { phase: "downloading", todo: todo.length });
  report();

  const failedIds = [];
  let buffer = [];
  let flushing = Promise.resolve();
  const flush = () => {
    if (!buffer.length) return flushing;
    const batch = buffer;
    buffer = [];
    flushing = flushing.then(() => onBatch(batch, account));
    return flushing;
  };

  let next = 0;
  let stopped = false;
  let authErr = null;
  const fields = "id,threadId,labelIds,internalDate,raw";
  const worker = async () => {
    while (next < todo.length && !authErr) {
      const id = todo[next++];
      try {
        const msg = await call(`messages/${encodeURIComponent(id)}?format=raw&fields=${fields}`);
        if (msg) {
          buffer.push(msg);
          if (buffer.length >= batchSize) await flush();
        }
      } catch (err) {
        if (err?.name === "AbortError") { stopped = true; return; }
        if (err instanceof AuthError) { authErr = err; return; }
        failedIds.push(id);
        state.failed++;
      }
      state.done++;
      state.waitingUntil = 0;
      report();
    }
  };
  await Promise.all(Array.from({ length: Math.min(concurrency, todo.length) }, worker));
  await flush();
  if (authErr) throw authErr;
  state.phase = "done";
  report();
  return { account, listed: ids.length, fetched: state.done - state.failed, failed: failedIds, stopped };
}
