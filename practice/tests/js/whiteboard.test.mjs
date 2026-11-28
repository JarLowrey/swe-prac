// The whiteboard's model (board-model.js) and the AI interviewer (interviewer.js): its prompts and
// the request and reply shapes of each AI service. The parts with no DOM, run in Node against the
// built site.
import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { data, importSite } from "./harness.mjs";

const board = await importSite("board-model.js");
const ai = await importSite("interviewer.js");
const speech = await importSite("transcribe.js");
const { LiveAudio } = await importSite("recorder.js");

const node = (id, kind, x, y, w, h, label) => ({ id, kind, x, y, w, h, label });

describe("board model", () => {
  test("old boards load: removed shapes open as boxes, a cloud as a circle; bad items are dropped", () => {
    const got = board.normalize({
      nodes: [
        node("a", "client", 0, 0, 120, 48, "Web"), node("b", "store", 300, 0, 130, 72, "DB"),
        node("c", "cloud", 0, 200, 160, 84, "CDN"), { kind: "box" }, node("d", "blob", 0, 400, 0, 0, ""),
      ],
      edges: [{ id: "e", from: "a", to: "b", label: "SQL" }, { id: "x", from: "a", to: "gone" }, { id: "self", from: "a", to: "a" }],
    });
    assert.deepEqual(got.nodes.map((n) => [n.id, n.kind]), [["a", "box"], ["b", "box"], ["c", "circle"], ["d", "box"]]);
    assert.equal(got.nodes[3].w, board.KINDS.box.w); // a missing size takes the kind's default
    assert.deepEqual(got.edges, [{ id: "e", from: "a", to: "b", label: "SQL", ends: "end", dash: false }]);
    assert.deepEqual(board.normalize(null), { nodes: [], edges: [] });
    assert.deepEqual(Object.keys(board.KINDS), ["text", "box", "circle", "diamond"]);
  });

  test("a line can end loose at a point; a loose end needs both coordinates", () => {
    const got = board.normalize({
      nodes: [node("a", "box", 0, 0, 100, 40, "API")],
      edges: [
        { id: "half", from: "a", to: null, x2: 300, y2: 20, ends: "none" },
        { id: "free", from: null, to: null, x1: 0, y1: 200, x2: 300, y2: 200, dash: true },
        { id: "dot", from: null, to: null, x1: 5, y1: 5, x2: 6, y2: 6 }, // too short to be a line
        { id: "bad", from: null, to: "a", x1: "10", y1: 10 }, // a string isn't a coordinate
      ],
    });
    assert.deepEqual(got.edges.map((e) => e.id), ["half", "free"]);
    assert.deepEqual(got.edges[0], { id: "half", from: "a", to: null, x2: 300, y2: 20, label: "", ends: "none", dash: false });
    assert.deepEqual(board.edgeGeometry(got.edges[0], new Map([["a", got.nodes[0]]])), { x1: 100, y1: 20, x2: 300, y2: 20 });
    assert.deepEqual(board.boardBounds(got), { x: 0, y: 0, w: 300, h: 200 });
    assert.equal(board.isEmpty({ nodes: [], edges: got.edges.slice(1) }), false);
  });

  test("text is sized to its lines; shapes grow to fit but never shrink", () => {
    const text = board.fitNode(node("t", "text", 0, 0, 1, 1, "one\ntwo\nthree"));
    assert.equal(text.h, 3 * board.LINE + 8);
    const box = board.fitNode(node("b", "box", 0, 0, 140, 60, "Service"));
    assert.deepEqual([box.w, box.h], [140, 60]);
    const long = board.fitNode(node("b", "box", 0, 0, 140, 60, "A much longer service name here\nand a second line\nand a third"));
    assert.ok(long.w > 140 && long.h > 60, `${long.w}x${long.h}`);
    const entity = board.fitNode(node("e", "box", 0, 0, 140, 60, "# Paste\nid\ncontent\nexpires_at\nowner_id"));
    assert.ok(entity.h >= 5 * board.LINE, String(entity.h));
  });

  test("arrows end on each shape's outline", () => {
    const box = node("b", "box", 0, 0, 100, 40, "");
    assert.deepEqual(board.boundary(box, 500, 20), [100, 20]);
    const circle = node("c", "circle", 0, 0, 100, 100, "");
    const [x, y] = board.boundary(circle, 50 + 300, 50 + 300);
    assert.ok(Math.abs(Math.hypot(x - 50, y - 50) - 50) < 1e-9);
    const diamond = node("d", "diamond", 0, 0, 100, 60, "");
    assert.deepEqual(board.boundary(diamond, 50, 500), [50, 60]);
  });

  test("a shape holds what sits entirely inside it; text holds nothing", () => {
    const outer = node("o", "box", 0, 0, 400, 300, "Region");
    const inner = node("i", "circle", 20, 40, 130, 100, "DB");
    const label = node("t", "text", 40, 70, 60, 26, "shard 1"); // inside both: the smaller one holds it
    const outside = node("x", "text", 380, 280, 60, 26, "half out");
    const nodes = [outer, inner, label, outside];
    assert.equal(board.containerOf(label, nodes).id, "i");
    assert.equal(board.containerOf(inner, nodes).id, "o");
    assert.equal(board.containerOf(outside, nodes), null);
    assert.deepEqual(board.contents(outer, nodes).map((n) => n.id), ["i", "t"]);
    assert.deepEqual(board.contents(label, nodes), []);
    // Bigger shapes are drawn first, free text last.
    assert.deepEqual(board.paintOrder(nodes).map((n) => n.id), ["o", "i", "t", "x"]);
    // A box holding items is a frame (label at the top); a circle holding text is not.
    assert.deepEqual([...board.framedIds(nodes)], ["o"]);
  });

  test("double-clicking a roomy shape away from its label adds text there", () => {
    const big = node("b", "box", 0, 0, 300, 200, "Region");
    assert.equal(board.makesTextAt(big, { x: 150, y: 100 }), false); // on the centered label
    assert.equal(board.makesTextAt(big, { x: 150, y: 170 }), true);
    assert.equal(board.makesTextAt(big, { x: 150, y: 20 }, true), false); // a frame's label is at the top
    assert.equal(board.makesTextAt(big, { x: 150, y: 100 }, true), true);
    assert.equal(board.makesTextAt(node("s", "box", 0, 0, 140, 60, "API"), { x: 70, y: 55 }), false); // too small
    assert.equal(board.makesTextAt(node("t", "text", 0, 0, 300, 300, "notes"), { x: 150, y: 250 }), false);
  });

  test("the board as text nests items under their shape and lists every line and arrow", () => {
    const model = {
      nodes: [
        node("req", "text", 0, 0, 200, 80, "# Requirements\nFunctional:\n- create a paste"),
        node("api", "box", 0, 200, 300, 200, "API"),
        node("note", "text", 20, 330, 80, 26, "stateless"),
        node("db", "circle", 400, 200, 130, 100, "Pastes\nid, body"),
        node("lb", "diamond", 400, 0, 160, 84, ""),
      ],
      edges: [
        { id: "e1", from: "api", to: "db", label: "write", ends: "end" },
        { id: "e2", from: "lb", to: "api", label: "", ends: "both", dash: true },
        { id: "e3", from: "db", to: null, x2: 700, y2: 250, label: "replicas", ends: "none" },
      ],
    };
    assert.equal(board.boardText(model), [
      "- Text: Requirements",
      "    Functional:",
      "    - create a paste",
      "- Diamond: (no label)",
      "- Box: API",
      "  - Text: stateless",
      "- Circle: Pastes",
      "    id, body",
      "",
      "Lines and arrows:",
      '- Box "API" → Circle "Pastes / id, body": write',
      '- Diamond (no label) ↔ Box "API" (dashed)',
      '- Circle "Pastes / id, body" — (loose end): replicas',
    ].join("\n"));
    assert.equal(board.boardText({}), "(The board is empty.)");
    assert.equal(board.boardText({ edges: [{ from: null, to: null, x1: 0, y1: 0, x2: 50, y2: 0 }] }),
      "Lines and arrows:\n- (loose end) → (loose end)");
  });
});

describe("AI services", () => {
  const prompts = { system: "SYSTEM", user: "USER" };

  test("Gemini: one generateContent call with the key in a header and low thinking on Gemini 3+", () => {
    const { url, init } = ai.geminiRequest({ key: "k1", model: "gemini-4-hydrogen" }, prompts);
    assert.equal(url, "https://generativelanguage.googleapis.com/v1beta/models/gemini-4-hydrogen:generateContent");
    assert.equal(init.headers["x-goog-api-key"], "k1");
    assert.ok(!url.includes("k1"));
    const body = JSON.parse(init.body);
    assert.deepEqual(body.systemInstruction, { parts: [{ text: "SYSTEM" }] });
    assert.deepEqual(body.contents, [{ role: "user", parts: [{ text: "USER" }] }]);
    assert.deepEqual(body.generationConfig.thinkingConfig, { thinkingLevel: "LOW" });
    const older = JSON.parse(ai.geminiRequest({ key: "k", model: "gemini-2.5-flash" }, prompts).init.body);
    assert.equal(older.generationConfig.thinkingConfig, undefined); // earlier models reject thinkingLevel
  });

  test("Gemini replies: text without thoughts; blocks read as declined", () => {
    const reply = ai.geminiReply({ modelVersion: "gemini-4-hydrogen", candidates: [{ content: { parts: [{ text: "plan", thought: true }, { text: "Yes." }] }, finishReason: "STOP" }] });
    assert.deepEqual(reply, { text: "Yes.", model: "gemini-4-hydrogen" });
    assert.deepEqual(ai.geminiReply({ promptFeedback: { blockReason: "SAFETY" } }), { declined: true });
    assert.deepEqual(ai.geminiReply({ candidates: [{ finishReason: "SAFETY" }] }), { declined: true });
  });

  test("ChatGPT: one Responses call, not stored, low reasoning on reasoning models", () => {
    const { url, init } = ai.openaiRequest({ key: "k2", model: "gpt-6.2-astra" }, prompts);
    assert.equal(url, "https://api.openai.com/v1/responses");
    assert.equal(init.headers.authorization, "Bearer k2");
    const body = JSON.parse(init.body);
    assert.deepEqual([body.model, body.instructions, body.input, body.store], ["gpt-6.2-astra", "SYSTEM", "USER", false]);
    assert.deepEqual(body.reasoning, { effort: "low" });
    const plain = JSON.parse(ai.openaiRequest({ key: "k", model: "gpt-4.1" }, prompts).init.body);
    assert.equal(plain.reasoning, undefined);
  });

  test("ChatGPT replies: the message text; a refusal reads as declined", () => {
    const json = { model: "gpt-6.2-astra", output: [{ type: "reasoning", summary: [] }, { type: "message", content: [{ type: "output_text", text: "No. Wrong store." }] }] };
    assert.deepEqual(ai.openaiReply(json), { text: "No. Wrong store.", model: "gpt-6.2-astra" });
    assert.deepEqual(ai.openaiReply({ output: [{ type: "message", content: [{ type: "refusal", refusal: "no" }] }] }), { declined: true });
  });

  test("HTTP errors read as plain advice", () => {
    assert.match(ai.httpError("gemini", 400, { error: { message: "API key not valid. Please pass a valid API key." } }), /key was rejected/);
    assert.match(ai.httpError("openai", 401, null), /key was rejected/);
    assert.match(ai.httpError("openai", 404, null), /model isn't available/);
    assert.match(ai.httpError("gemini", 429, null), /Rate limited/);
    assert.equal(ai.httpError("openai", 400, { error: { message: "Bad input" } }), "The OpenAI API refused the request: Bad input");
    assert.deepEqual(Object.keys(ai.PROVIDERS), ["claude", "gemini", "openai"]);
    assert.equal(ai.modelName("openai", "gpt-6.2-astra"), "GPT-6.2 Astra");
    assert.equal(ai.modelName("gemini", "gemini-custom-1"), "gemini-custom-1");
  });

  test("a blocked request: OpenAI's points at the key too (its 401 has no CORS header)", async () => {
    const real = globalThis.fetch;
    globalThis.fetch = async () => { throw new TypeError("Failed to fetch"); };
    try {
      const settings = (provider, model) => ({ provider, model, key: "bad" });
      await assert.rejects(ai.askApi(settings("openai", "gpt-6.2-astra"), prompts), /Couldn't reach the OpenAI API\. Check the key and model/);
      await assert.rejects(ai.askApi(settings("gemini", "gemini-4-hydrogen"), prompts), /^Error: Couldn't reach the Gemini API\. Check your connection\.$/);
    } finally {
      globalThis.fetch = real;
    }
  });
});

describe("AI interviewer prompts", () => {
  const item = data.design.questions[0];
  const notes = {
    hard_part: item.hints.hard_part, building_blocks: item.hints.building_blocks,
    key_points: item.key_points, reference_md: item.reference_md,
  };
  const ctx = {
    question: item.question,
    elapsed: 2760,
    limit: 2700,
    board: { nodes: [node("a", "box", 0, 0, 140, 56, "Paste service")], edges: [] },
    hints: [{ profile: "strict", question: "Do I need a cache?", answer: "Yes." }],
  };

  test("the API prompt carries the interviewer notes; the paste prompt never does", () => {
    const system = ai.systemPrompt("strict", notes);
    assert.ok(system.includes(item.key_points[0]));
    assert.ok(system.includes(item.reference_md.trim()));
    assert.match(system, /Start with "Yes\." or "No\."/);
    const pasted = ai.pastePrompt("helpful", ctx, "What next?");
    assert.ok(!pasted.includes(item.reference_md.trim()));
    assert.ok(!pasted.includes(item.key_points[0]));
    assert.match(pasted, /About three sentences/);
    assert.throws(() => ai.systemPrompt("nice", notes));
  });

  test("the request shows the time, the board and the hints already given, and no steps", () => {
    const user = ai.userPrompt(ctx, "  Should I shard?  ");
    assert.doesNotMatch(user, /\bstep\b/i);
    assert.doesNotMatch(ai.systemPrompt("helpful", notes), /this step|step of the interview/i);
    assert.match(user, /Time used: 46:00 of 45:00 \(1:00 into overtime\)/);
    assert.match(user, /- Box: Paste service/);
    assert.match(user, /\[Strict\] Q: Do I need a cache\?\nA: Yes\./);
    assert.match(user, /The candidate asks: Should I shard\?/);
    assert.match(ai.userPrompt({ ...ctx, hints: [] }, ""), /asks for a hint without a question/);
    assert.match(ai.userPrompt({ ...ctx, hints: [] }, ""), /\(none yet\)/);
  });

  test("the paste prompt carries what the candidate said, at session times, when there's a transcript", () => {
    const said = [{ at: 12.4, text: "Reads dominate, so a cache first." }, { at: 605, text: "Then shard by paste key." }];
    const pasted = ai.pastePrompt("strict", { ...ctx, transcript: said }, "Am I on track?");
    assert.match(pasted, /<transcript>\n[^<]*machine \(expect misheard words\)[^<]*\n\[0:12\] Reads dominate, so a cache first\.\n\[10:05\] Then shard by paste key\.\n<\/transcript>/);
    assert.ok(pasted.indexOf("</board>") < pasted.indexOf("<transcript>"));
    assert.ok(pasted.indexOf("</transcript>") < pasted.indexOf("<earlier_hints>"));
    assert.match(ai.systemPrompt("strict"), /machine transcript of what they've said/);
    for (const transcript of [undefined, null, []]) {
      assert.doesNotMatch(ai.userPrompt({ ...ctx, transcript }, ""), /<transcript>/);
    }
  });

  test("the strict verdict is read from the start of the answer", () => {
    assert.equal(ai.verdict("Yes. Obviously."), "yes");
    assert.equal(ai.verdict("  no."), "no");
    assert.equal(ai.verdict("**No.** Wrong store."), "no");
    assert.equal(ai.verdict("Not quite"), null);
    assert.equal(ai.verdict("Yesterday's data"), null);
  });
});

describe("recording transcript (transcribe.js)", () => {
  const RATE = speech.RATE;
  // A 440 Hz tone with silent gaps: [start, end) in seconds.
  function audio(seconds, gaps = []) {
    const samples = new Float32Array(seconds * RATE);
    for (let i = 0; i < samples.length; i++) samples[i] = 0.1 * Math.sin((2 * Math.PI * 440 * i) / RATE);
    for (const [a, b] of gaps) samples.fill(0, a * RATE, b * RATE);
    return samples;
  }

  test("audio goes to Whisper in pieces of at most 30 s, cut where it's quiet", () => {
    const samples = audio(75, [[24, 24.2], [50, 50.3]]);
    const got = speech.pieces(samples);
    assert.equal(got.length, 3);
    assert.equal(got[0][0], 0);
    assert.equal(got.at(-1)[1], samples.length);
    for (let i = 1; i < got.length; i++) assert.equal(got[i][0], got[i - 1][1]); // no gaps, no overlap
    for (const [a, b] of got) assert.ok(b - a <= 30 * RATE);
    const cuts = got.slice(0, -1).map(([, b]) => b / RATE);
    assert.ok(cuts[0] > 24 && cuts[0] < 24.2, `first cut at ${cuts[0]}`);
    assert.ok(cuts[1] > 50 && cuts[1] < 50.3, `second cut at ${cuts[1]}`);
  });

  test("pieces start where the saved transcript ends; short audio is one piece", () => {
    const samples = audio(75);
    assert.deepEqual(speech.pieces(samples, 70 * RATE), [[70 * RATE, 75 * RATE]]);
    assert.deepEqual(speech.pieces(samples, 75 * RATE), []);
    assert.deepEqual(speech.pieces(audio(12)), [[0, 12 * RATE]]);
    assert.deepEqual(speech.pieces(new Float32Array(0)), []);
    // No quiet moment: still cut between 20 and 30 s in.
    const cut = speech.pieces(samples)[0][1] / RATE;
    assert.ok(cut >= 20 && cut <= 30, `cut at ${cut}`);
  });

  test("the recording being made goes in short pieces, so little is left when a prompt asks", () => {
    const got = speech.pieces(audio(28, [[9, 9.2], [17, 17.2]]), 0, { min: 6, max: 12 });
    const cuts = got.slice(0, -1).map(([, b]) => b / RATE);
    assert.equal(got.length, 3);
    assert.ok(cuts[0] > 9 && cuts[0] < 9.2, `first cut at ${cuts[0]}`);
    assert.ok(cuts[1] > 17 && cuts[1] < 17.2, `second cut at ${cuts[1]}`);
    for (const [a, b] of got) assert.ok(b - a <= 12 * RATE);
  });

  test("tags for sounds that aren't speech are dropped from Whisper's text", () => {
    assert.equal(speech.cleanText(" [BLANK_AUDIO] "), "");
    assert.equal(speech.cleanText(" So, (upbeat music) a cache  first. "), "So, a cache first.");
    assert.equal(speech.cleanText(undefined), "");
    assert.equal(speech.cleanText(" . "), ""); // no word in it
    assert.equal(speech.cleanText("Maybe 100 to 1."), "Maybe 100 to 1.");
  });

  test("a recording keeps the model it was started with; older ones use the accurate one", () => {
    const { fast, accurate } = speech.MODELS;
    assert.equal(speech.DEFAULT_SPEECH, "accurate");
    assert.equal(speech.clipModel({ speech: "fast" }), fast);
    assert.equal(speech.clipModel({ speech: "accurate" }), accurate);
    assert.equal(speech.clipModel({}), accurate); // recorded before there was a choice
    assert.equal(speech.clipModel({ speech: "fast" }, { model: accurate.id }), accurate); // its transcript says
    assert.equal(speech.clipModel({ speech: "fast" }, { model: "gone/model" }), fast);
    assert.ok(fast.mb < accurate.mb);
    for (const m of [fast, accurate]) assert.match(m.revision, /^[0-9a-f]{40}$/);
  });

  test("each recording's lines are placed at the session time it started", () => {
    const clips = [{ id: "a", started_at: 30 }, { id: "b", started_at: 600 }, { id: "c", started_at: 900 }];
    const transcripts = new Map([
      ["a", { segments: [{ start: 0, end: 4, text: "Requirements first." }, { start: 4.5, end: 9, text: "Reads dominate." }] }],
      ["b", { segments: [{ start: 2, end: 6, text: "Now the cache." }] }],
    ]);
    assert.deepEqual(speech.transcriptLines(clips, transcripts), [
      { at: 30, text: "Requirements first." }, { at: 34.5, text: "Reads dominate." }, { at: 602, text: "Now the cache." },
    ]);
  });
});

describe("live audio kept for transcribing (recorder.js)", () => {
  const block = (start, n = 4) => Float32Array.from({ length: n }, (_, i) => start + i);

  test("samples come back from any time not yet released, across blocks", () => {
    const live = new LiveAudio("c1", 4); // 4 samples a second: one block each second
    for (let s = 0; s < 3; s++) live.push(block(s * 4));
    assert.equal(live.seconds, 3);
    assert.deepEqual([...live.from(0)], [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
    assert.deepEqual([...live.from(1.5)], [6, 7, 8, 9, 10, 11]);
    assert.deepEqual([...live.from(3)], []);
  });

  test("release drops whole blocks before the time; earlier samples are then gone", () => {
    const live = new LiveAudio("c1", 4);
    for (let s = 0; s < 3; s++) live.push(block(s * 4));
    live.release(1.5); // the block for 1-2 s is still needed from 1.5 s
    assert.equal(live.blocks.length, 2);
    assert.deepEqual([...live.from(1.5)], [6, 7, 8, 9, 10, 11]);
    assert.equal(live.from(0.5), null);
    assert.equal(live.seconds, 3);
  });

  test("falling too far behind drops it all, so the saved file is decoded instead", () => {
    const live = new LiveAudio("c1", 4, 2); // keep at most 2 s
    live.push(block(0));
    live.push(block(4));
    assert.ok(!live.lost);
    live.push(block(8));
    assert.ok(live.lost);
    assert.equal(live.from(2), null);
    assert.equal(live.blocks.length, 0);
  });
});
