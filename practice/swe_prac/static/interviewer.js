// The AI interviewer of a system design session. Two personas answer hint requests:
//   strict    yes or no, a few curt words at most
//   helpful   about three sentences of background or a follow-up nudge
// It runs two ways. With the visitor's own API key for Claude, Gemini or ChatGPT (OpenAI), the
// page calls that API directly from the browser; the key never leaves this browser except to
// that API. Without one, the page builds a prompt to paste into any AI agent, and the visitor
// pastes the reply back.
//
// The API request carries the question's interviewer notes (key points and the reference design)
// so the verdicts are grounded; the page never shows them. The paste prompt leaves them out,
// because the visitor reads what they paste. When the session has a recording, the paste prompt
// carries its transcript (transcribe.js, made in the browser).
//
// No DOM at import time: tests/js/ imports the prompt builders and request shapes in Node.

import { boardText } from "./board-model.js";

export const PERSONAS = {
  strict: { name: "Strict", blurb: "Yes or no, and not a word more." },
  helpful: { name: "Helpful", blurb: "About three sentences of background or a follow-up nudge." },
};

// The services a visitor can bring a key for. models: [id, name], the first is the default; AI
// settings also takes any other model ID the service offers.
export const PROVIDERS = {
  claude: {
    name: "Claude", api: "Claude API", keyUrl: "https://platform.claude.com",
    models: [["claude-opus-5-5", "Opus 5.5"], ["claude-sonnet-5-5", "Sonnet 5.5"], ["claude-haiku-5-5", "Haiku 5.5"]],
  },
  gemini: {
    name: "Gemini", api: "Gemini API", keyUrl: "https://aistudio.google.com/apikey",
    models: [["gemini-4-hydrogen", "Gemini 4 Hydrogen"], ["gemini-4-carbon", "Gemini 4 Carbon"], ["gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite"]],
  },
  openai: {
    name: "ChatGPT", api: "OpenAI API", keyUrl: "https://platform.openai.com/api-keys",
    models: [["gpt-6.2-astra", "GPT-6.2 Astra"], ["gpt-6.2-sol", "GPT-6.2 Sol"], ["gpt-6-luna", "GPT-6 Luna"]],
  },
};
export const modelName = (provider, id) => PROVIDERS[provider]?.models.find(([m]) => m === id)?.[1] ?? id;
const MODEL_ID = /^[\w.:-]{1,100}$/;

// ---------------------------------------------------------------- prompts
const fmt = (seconds) => {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};

const SETTING = `You are the interviewer in a 45-minute system design interview. The candidate works on a
shared whiteboard and asks you for hints as they go. The round isn't split into steps: judge their
progress from the time used and what's on the board. Each request gives you the question, the
time used, their whiteboard written out as text (each shape and text block, nested under the shape
it sits inside, then every line and arrow), and the hints you already gave this session. When they
record themselves talking it through, it also gives a machine transcript of what they've said, so
you can judge their reasoning as well as the board.`;

const RULES = {
  strict: `You are strict and grumpy: a senior engineer who has run too many of these interviews and
answers with a verdict, nothing else.

How you answer:
- Start with "Yes." or "No." and add at most four more words, curt and never warm. For example:
  "Yes.", "Yes. Obviously.", "No.", "No. Wrong store.", "No. Think harder."
- Never explain, teach, list options or ask a question back.
- A request with no question means "Am I on track?": answer "Yes." if their board is where it
  should be for the time used, "No." if something important is missing or wrong.
- If the question isn't a yes/no question, answer the closest yes/no reading of it.`,
  helpful: `You are friendly and helpful: a senior engineer who wants the candidate to do well and
steers them without giving the answer away.

How you answer:
- About three sentences, never more than four. Plain text: no lists, headings or markdown.
- Give the background they need (the concept, trade-off or rough numbers behind the decision in
  front of them), or a follow-up question that points at what to consider next.
- Nudge, don't solve: never hand over the whole design.
- A request with no question means "What should I think about next?": give the most useful
  nudge for the time used and what's on the board.
- If their approach differs from what you expected but is reasonable, say so and help them make
  it work.
- Don't repeat a hint you already gave.`,
};

function notesBlock(notes) {
  if (!notes) {
    return "You have no answer key for this question: judge from your own system design experience.";
  }
  const points = notes.key_points.map((p) => `- ${p}`).join("\n");
  return `Your interviewer notes follow. The candidate can't see them. Use them to judge and to aim
your hints; never quote them or reveal them.

<hard_part>${notes.hard_part}</hard_part>
<building_blocks>${notes.building_blocks.join(", ")}</building_blocks>
<key_points>
${points}
</key_points>
<reference_design>
${notes.reference_md.trim()}
</reference_design>`;
}

// The system prompt: the setting, the persona's rules, then the notes (or the lack of them). It
// stays the same for every request in a session, so the API can cache it.
export function systemPrompt(persona, notes = null) {
  if (!RULES[persona]) throw new Error(`Unknown persona '${persona}'`);
  return `${SETTING}\n\n${RULES[persona]}\n\n${notesBlock(notes)}`;
}

// What the candidate said, one line per spoken sentence or so, at its session time. Machine
// transcription mishears words, technical terms most of all, so the prompt says so.
function transcriptBlock(lines) {
  if (!lines?.length) return "";
  return `
<transcript>
What the candidate has said out loud so far, transcribed by machine (expect misheard words), at
the session time each line starts:
${lines.map((l) => `[${fmt(l.at)}] ${l.text}`).join("\n")}
</transcript>`;
}

// ctx: {question: {title, prompt}, elapsed, limit, board, hints: [{profile, question, answer}],
//       transcript?: [{at, text}]}
export function userPrompt(ctx, ask) {
  const { question } = ctx;
  const over = ctx.elapsed > ctx.limit ? ` (${fmt(ctx.elapsed - ctx.limit)} into overtime)` : "";
  const earlier = ctx.hints?.length
    ? ctx.hints.map((h) => `[${PERSONAS[h.profile]?.name ?? h.profile}] ${h.question ? `Q: ${h.question}` : "(hint request, no question)"}\nA: ${h.answer}`).join("\n\n")
    : "(none yet)";
  const request = ask?.trim()
    ? `The candidate asks: ${ask.trim()}`
    : "The candidate asks for a hint without a question.";
  return `<question>
${question.title}: ${question.prompt}
</question>
<progress>
Time used: ${fmt(ctx.elapsed)} of ${fmt(ctx.limit)}${over}.
</progress>
<board>
${boardText(ctx.board)}
</board>${transcriptBlock(ctx.transcript)}
<earlier_hints>
${earlier}
</earlier_hints>
<request>
${request}
</request>`;
}

// One block of text to paste into any AI agent. No interviewer notes: the visitor reads it.
export function pastePrompt(persona, ctx, ask) {
  return `Play the interviewer described below. Reply with your answer to the candidate only.

${systemPrompt(persona, null)}

${userPrompt(ctx, ask)}`;
}

// "yes", "no" or null: the strict persona's verdict, for the ✓/✗ mark.
export function verdict(text) {
  const m = /^\W*(yes|no)\b/i.exec(String(text ?? ""));
  return m ? m[1].toLowerCase() : null;
}

// ---------------------------------------------------------------- settings
// The chosen service and each service's model are kept in localStorage. Each service's key goes
// to localStorage when "remember" is on, otherwise to sessionStorage (gone when the tab closes).
// None of it is in the history export.
const SETTINGS_KEY = "swe-prac-ai";
const keyName = (provider) => `swe-prac-ai-key-${provider}`;
const OLD_KEY = "swe-prac-ai-key"; // the Claude key, saved before Gemini and ChatGPT were added

function read(store, key) {
  try { return store.getItem(key); } catch { return null; }
}
function write(store, key, value) {
  try {
    if (value == null) store.removeItem(key); else store.setItem(key, value);
  } catch { /* storage refused: the key lasts for this page only */ }
}

const pageKeys = {}; // when the browser refuses both stores

function saved() {
  let s = {};
  try { s = JSON.parse(read(localStorage, SETTINGS_KEY) ?? "{}") ?? {}; } catch { s = {}; }
  const models = typeof s.models === "object" && s.models ? { ...s.models } : {};
  if (typeof s.model === "string" && !models.claude) models.claude = s.model; // the old shape
  return { provider: PROVIDERS[s.provider] ? s.provider : "claude", models };
}

// {provider, model, key, remember} for the chosen service, or for `provider` when given.
export function aiSettings(provider = null) {
  const s = saved();
  const p = PROVIDERS[provider] ? provider : s.provider;
  const model = typeof s.models[p] === "string" && MODEL_ID.test(s.models[p]) ? s.models[p] : PROVIDERS[p].models[0][0];
  const old = p === "claude";
  const remembered = read(localStorage, keyName(p)) ?? (old ? read(localStorage, OLD_KEY) : null);
  const key = remembered ?? read(sessionStorage, keyName(p)) ?? (old ? read(sessionStorage, OLD_KEY) : null) ?? pageKeys[p] ?? "";
  return { provider: p, model, key, remember: remembered != null };
}

// Saves one service's model and key, and makes it the chosen one.
export function saveAiSettings({ provider, model, key, remember }) {
  if (!PROVIDERS[provider]) throw new Error(`Unknown AI service '${provider}'`);
  const s = saved();
  const id = String(model ?? "").trim();
  s.models[provider] = MODEL_ID.test(id) ? id : PROVIDERS[provider].models[0][0];
  write(localStorage, SETTINGS_KEY, JSON.stringify({ provider, models: s.models }));
  const value = key?.trim() || null;
  pageKeys[provider] = value;
  write(localStorage, keyName(provider), remember ? value : null);
  write(sessionStorage, keyName(provider), remember ? null : value);
  if (provider === "claude") { write(localStorage, OLD_KEY, null); write(sessionStorage, OLD_KEY, null); }
}

// ---------------------------------------------------------------- the APIs
const MAX_TOKENS = 16000; // room for the model's thinking; the answers themselves are short

// Claude, through the official SDK (bundled in vendor/anthropic, loaded on first use).
// Models that can re-run a declined request on another model, server side (Haiku can't).
const SERVER_FALLBACK = new Set(["claude-opus-5-5", "claude-sonnet-5-5"]);
const CLAUDE_EFFORT = /^claude-(opus|sonnet|haiku|fable|mythos)-5/; // models that take `effort`
let sdk = null;
const loadSdk = () => (sdk ??= import("./vendor/anthropic/anthropic-sdk.mjs").catch((err) => {
  sdk = null;
  throw err;
}));

function claudeError(err, m) {
  if (err instanceof m.AuthenticationError) return "The API key was rejected. Check it in AI settings.";
  if (err instanceof m.PermissionDeniedError) return "This API key isn't allowed to use that model.";
  if (err instanceof m.NotFoundError) return "That model isn't available to this API key. Pick another in AI settings.";
  if (err instanceof m.RateLimitError) return "Rate limited. Wait a moment and ask again.";
  if (err instanceof m.BadRequestError) return `The API refused the request: ${err.message}`;
  if (err instanceof m.APIUserAbortError) return "Cancelled.";
  if (err instanceof m.APIConnectionError) return "Couldn't reach the API. Check your connection.";
  if (err instanceof m.APIError) return err.status >= 500 ? "The API is having trouble. Try again." : `The API returned an error: ${err.message}`;
  return err.message;
}

async function askClaude({ key, model }, { system, user }, signal) {
  let m;
  try { m = await loadSdk(); } catch { throw new Error("Couldn't load the API client. Reload the page and try again."); }
  const client = new m.Anthropic({ apiKey: key, dangerouslyAllowBrowser: true, maxRetries: 1 });
  const params = {
    model,
    max_tokens: MAX_TOKENS,
    ...(CLAUDE_EFFORT.test(model) ? { output_config: { effort: "low" } } : {}), // short answers, short waits
    // The same for every hint in a session, so repeat requests read it from the prompt cache.
    system: [{ type: "text", text: system, cache_control: { type: "ephemeral" } }],
    messages: [{ role: "user", content: user }],
  };
  let message;
  try {
    message = SERVER_FALLBACK.has(model)
      // If the model declines, the API re-runs the request on a fallback model in the same call.
      ? await client.beta.messages.create({ ...params, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default" }, { signal })
      : await client.messages.create(params, { signal });
  } catch (err) {
    throw new Error(claudeError(err, m));
  }
  if (message.stop_reason === "refusal") throw new Error("The interviewer declined to answer that one. Try rewording it.");
  return { text: message.content.filter((b) => b.type === "text").map((b) => b.text).join(""), model: message.model };
}

// Gemini and OpenAI are plain HTTPS calls. Each builder returns {url, init} for fetch(); each
// reader turns the JSON reply into {text} or {declined: true}.
const GEMINI_THINKING = /^gemini-([3-9]|\d{2,})/; // thinkingLevel is for Gemini 3 and later

export function geminiRequest({ key, model }, { system, user }) {
  return {
    url: `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`,
    init: {
      method: "POST",
      headers: { "content-type": "application/json", "x-goog-api-key": key },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: system }] },
        contents: [{ role: "user", parts: [{ text: user }] }],
        generationConfig: {
          maxOutputTokens: MAX_TOKENS,
          ...(GEMINI_THINKING.test(model) ? { thinkingConfig: { thinkingLevel: "LOW" } } : {}),
        },
      }),
    },
  };
}

export function geminiReply(json) {
  if (json?.promptFeedback?.blockReason) return { declined: true };
  const candidate = json?.candidates?.[0];
  const parts = candidate?.content?.parts ?? [];
  const text = parts.filter((p) => !p.thought && typeof p.text === "string").map((p) => p.text).join("");
  if (!text && ["SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION"].includes(candidate?.finishReason)) return { declined: true };
  return { text, model: json?.modelVersion };
}

const OPENAI_REASONING = /^(gpt-[5-9]|o\d)/; // models that take reasoning.effort

export function openaiRequest({ key, model }, { system, user }) {
  return {
    url: "https://api.openai.com/v1/responses",
    init: {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${key}` },
      body: JSON.stringify({
        model,
        instructions: system,
        input: user,
        max_output_tokens: MAX_TOKENS,
        store: false, // the hint isn't kept on OpenAI's side for later retrieval
        ...(OPENAI_REASONING.test(model) ? { reasoning: { effort: "low" } } : {}),
      }),
    },
  };
}

export function openaiReply(json) {
  const content = (json?.output ?? []).filter((item) => item?.type === "message").flatMap((item) => item.content ?? []);
  const text = content.filter((c) => c?.type === "output_text").map((c) => c.text).join("");
  if (!text && content.some((c) => c?.type === "refusal")) return { declined: true };
  return { text, model: json?.model };
}

// A failed HTTP call as a message fit to show.
export function httpError(provider, status, json) {
  const detail = String(json?.error?.message ?? "").trim();
  const api = PROVIDERS[provider].api;
  if (status === 401 || status === 403 || /api key/i.test(detail)) return "The API key was rejected. Check it in AI settings.";
  if (status === 404) return "That model isn't available to this API key. Pick another in AI settings.";
  if (status === 429) return "Rate limited or out of quota. Wait a moment, or check your plan.";
  if (status >= 500) return `The ${api} is having trouble. Try again.`;
  return detail ? `The ${api} refused the request: ${detail}` : `The ${api} returned an error (${status}).`;
}

async function askHttp(provider, settings, prompts, signal) {
  const { url, init } = (provider === "gemini" ? geminiRequest : openaiRequest)(settings, prompts);
  let res;
  try {
    res = await fetch(url, { ...init, signal });
  } catch (err) {
    if (err?.name === "AbortError") throw new Error("Cancelled.");
    // OpenAI leaves the CORS header off some error replies (a wrong key, for one), so the browser
    // sees them as a failed request: point at the settings as well as the connection.
    const check = provider === "openai" ? "Check the key and model in AI settings, then your connection." : "Check your connection.";
    throw new Error(`Couldn't reach the ${PROVIDERS[provider].api}. ${check}`);
  }
  let json = null;
  try { json = await res.json(); } catch { /* not JSON */ }
  if (!res.ok) throw new Error(httpError(provider, res.status, json));
  const reply = (provider === "gemini" ? geminiReply : openaiReply)(json);
  if (reply.declined) throw new Error("The interviewer declined to answer that one. Try rewording it.");
  return reply;
}

// One hint: {text, model}. Throws an Error with a message fit to show.
export async function askApi(settings, prompts, { signal } = {}) {
  const { provider = "claude", key, model } = settings;
  if (!PROVIDERS[provider]) throw new Error("Pick an AI service in AI settings.");
  if (!key) throw new Error("Add your API key in AI settings first.");
  const reply = provider === "claude"
    ? await askClaude({ key, model }, prompts, signal)
    : await askHttp(provider, { key, model }, prompts, signal);
  const text = (reply.text ?? "").trim();
  if (!text) throw new Error("The interviewer had nothing to say. Ask again.");
  return { text, model: reply.model ?? model };
}
