// Sound-only recording of a system design session: talk through the design as you would in a real
// interview, then play it back on the review page. Recordings stay in this browser (IndexedDB),
// are never uploaded, and are not part of the history export (audio is large).
//
// A recording is saved every few seconds while it runs, so closing the tab keeps what was said.
// Pausing the session pauses the recording; ending the session stops it. A session can have
// several recordings (stop, then record again).
//
// The same database keeps each recording's transcript, which transcribe.js writes as the
// recording runs. While recording, the page also keeps the microphone's samples it hasn't
// transcribed yet (LiveAudio), so that it never has to decode the saved file to keep up.

const DB_NAME = "swe-prac-recordings";
const SLICE_MS = 5000;
const TYPES = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4", "audio/webm"];

export const recordingSupported = () => Boolean(globalThis.navigator?.mediaDevices?.getUserMedia && globalThis.MediaRecorder);

// ---------------------------------------------------------------- storage
let opening = null;
function db() {
  opening ??= new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 2);
    req.onupgradeneeded = (e) => {
      const d = req.result;
      if (e.oldVersion < 1) {
        d.createObjectStore("clips", { keyPath: "id" }).createIndex("session", "session_id");
        d.createObjectStore("chunks", { keyPath: ["clip", "seq"] }).createIndex("clip", "clip");
      }
      if (e.oldVersion < 2) d.createObjectStore("transcripts", { keyPath: "clip" });
    };
    // Another tab still has version 1 open: it closes its copy, and opens version 2 next time.
    req.onsuccess = () => { req.result.onversionchange = () => { req.result.close(); opening = null; }; resolve(req.result); };
    req.onerror = () => { opening = null; reject(req.error); };
  });
  return opening;
}

async function run(stores, mode, work) {
  const d = await db();
  return new Promise((resolve, reject) => {
    const tx = d.transaction(stores, mode);
    let out;
    Promise.resolve(work(tx)).then((v) => { out = v; }, reject);
    tx.oncomplete = () => resolve(out);
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error ?? new Error("Recording storage failed."));
  });
}
const done = (req) => new Promise((resolve, reject) => {
  req.onsuccess = () => resolve(req.result);
  req.onerror = () => reject(req.error);
});

// A session's recordings, oldest first: [{id, session_id, started_at, duration, mime, size, created}].
export async function listClips(sessionId) {
  const clips = await run(["clips"], "readonly", (tx) => done(tx.objectStore("clips").index("session").getAll(sessionId)));
  return clips.sort((a, b) => a.created - b.created);
}

export async function clipBlob(clip) {
  const chunks = await run(["chunks"], "readonly", (tx) => done(tx.objectStore("chunks").index("clip").getAll(clip.id)));
  chunks.sort((a, b) => a.seq - b.seq);
  return new Blob(chunks.map((c) => c.blob), { type: clip.mime });
}

export async function deleteClip(id) {
  await run(["clips", "chunks", "transcripts"], "readwrite", async (tx) => {
    tx.objectStore("clips").delete(id);
    tx.objectStore("transcripts").delete(id);
    const chunks = tx.objectStore("chunks");
    const keys = await done(chunks.index("clip").getAllKeys(id));
    for (const key of keys) chunks.delete(key);
  });
}

// A recording's transcript so far: {clip, model, upto, done, segments: [{start, end, text}]}, or
// null. upto: the seconds of audio transcribed for good; done: the whole recording is.
export const getTranscript = (clipId) => run(["transcripts"], "readonly", (tx) => done(tx.objectStore("transcripts").get(clipId)))
  .then((t) => t ?? null);

export async function putTranscript(transcript) {
  await run(["transcripts"], "readwrite", (tx) => { tx.objectStore("transcripts").put(transcript); });
}

export const clipExtension = (mime) => (mime.includes("ogg") ? "ogg" : mime.includes("mp4") ? "m4a" : "webm");

// ---------------------------------------------------------------- live audio
// The samples of a recording made on this page, as the microphone hands them over (pcm-tap.js),
// so transcribe.js can transcribe as it goes without decoding the saved file again and again.
// Only what isn't transcribed yet is kept: release() drops the rest. If transcription falls more
// than `limit` seconds behind, it's all dropped (lost), and transcribe.js decodes the file instead.
export class LiveAudio {
  constructor(clip, rate, limit = 600) {
    Object.assign(this, { clip, rate, limit, start: 0, held: 0, blocks: [], lost: false });
  }

  push(block) {
    if (this.lost) return;
    this.blocks.push(block);
    this.held += block.length;
    if (this.held > this.limit * this.rate) Object.assign(this, { lost: true, blocks: [], held: 0 });
  }

  // Where the samples end, in seconds from the start of the recording.
  get seconds() { return (this.start + this.held) / this.rate; }

  // The samples from `seconds` on, or null if some of them are gone.
  from(seconds) {
    const first = Math.round(seconds * this.rate);
    if (this.lost || first < this.start) return null;
    const out = new Float32Array(Math.max(0, this.start + this.held - first));
    let pos = this.start;
    let at = 0;
    for (const block of this.blocks) {
      const skip = Math.max(0, first - pos);
      if (skip < block.length) { out.set(skip ? block.subarray(skip) : block, at); at += block.length - skip; }
      pos += block.length;
    }
    return out;
  }

  // Drops the samples before `seconds`: they're transcribed for good.
  release(seconds) {
    const upto = Math.floor(seconds * this.rate);
    while (this.blocks.length && this.start + this.blocks[0].length <= upto) {
      const [block] = this.blocks.splice(0, 1);
      this.start += block.length;
      this.held -= block.length;
    }
  }
}

// The microphone's samples, through an AudioWorklet. Resolves to {context, connect} or null when
// the browser can't (transcription then decodes the saved file).
async function openTap(stream, onBlock) {
  let context;
  try {
    context = new AudioContext();
    await context.audioWorklet.addModule(new URL("pcm-tap.js", import.meta.url));
    const node = new AudioWorkletNode(context, "pcm-tap", { numberOfOutputs: 1, outputChannelCount: [1] });
    node.port.onmessage = (e) => onBlock(e.data);
    const mute = context.createGain();
    mute.gain.value = 0; // pulled by the speakers, so it runs, but silent
    node.connect(mute).connect(context.destination);
    const source = context.createMediaStreamSource(stream);
    return { context, connect: () => { source.connect(node); context.resume().catch(() => {}); } };
  } catch (err) {
    console.warn("No live audio for transcription; it will decode the recording instead.", err);
    context?.close().catch(() => {});
    return null;
  }
}

// ---------------------------------------------------------------- recording
// elapsed(): the session clock, so the review can say when in the session a recording began.
// onChange(): called whenever the state (recording, paused, stopped) or the saved length changes.
export function createRecorder({ sessionId, elapsed, onChange = () => {} }) {
  let rec = null;
  let stream = null;
  let clip = null;
  let seq = 0;
  let activeMs = 0;
  let since = 0;
  let saving = Promise.resolve();
  let flushed = []; // resolvers waiting for the next chunk to be saved
  let tap = null; // the AudioWorklet feeding `audio`, while recording
  let audio = null; // LiveAudio of the latest recording made here (kept after it stops)

  const state = () => rec?.state ?? "inactive"; // "recording" | "paused" | "inactive"
  const seconds = () => (activeMs + (rec?.state === "recording" ? performance.now() - since : 0)) / 1000;

  function save(blob) {
    const chunk = { clip: clip.id, seq: seq++, blob };
    const record = { ...clip, duration: seconds(), size: clip.size + blob.size };
    clip = record;
    saving = saving.then(() => run(["clips", "chunks"], "readwrite", (tx) => {
      tx.objectStore("chunks").put(chunk);
      tx.objectStore("clips").put(record);
    })).catch((err) => console.warn("Recording chunk not saved", err));
  }

  // extra: fields kept on the recording's record, e.g. {speech} (the model to transcribe it with).
  async function start(extra = {}) {
    if (state() !== "inactive") return;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    } catch (err) {
      throw new Error(err?.name === "NotAllowedError" ? "The microphone is blocked. Allow it in this site's browser settings."
        : err?.name === "NotFoundError" ? "No microphone found." : `The microphone didn't start: ${err?.message ?? err}`);
    }
    const type = TYPES.find((t) => MediaRecorder.isTypeSupported(t));
    rec = new MediaRecorder(stream, type ? { mimeType: type, audioBitsPerSecond: 48000 } : undefined);
    clip = {
      ...extra,
      id: `c${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`,
      session_id: sessionId, started_at: elapsed(), created: Date.now(),
      mime: rec.mimeType || type || "audio/webm", duration: 0, size: 0,
    };
    seq = 0;
    activeMs = 0;
    await run(["clips"], "readwrite", (tx) => { tx.objectStore("clips").put(clip); });
    rec.ondataavailable = (e) => {
      if (e.data.size) save(e.data);
      const waiting = flushed;
      flushed = [];
      saving.then(() => waiting.forEach((resolve) => resolve()));
    };
    tap = await openTap(stream, (block) => audio?.push(block)); // blocks flow once connected
    audio = tap ? new LiveAudio(clip.id, tap.context.sampleRate) : null;
    rec.start(SLICE_MS);
    tap?.connect(); // the samples start with the recording, so their times match
    since = performance.now();
    onChange();
  }

  function pause() {
    if (state() !== "recording") return;
    rec.pause();
    tap?.context.suspend().catch(() => {});
    activeMs += performance.now() - since;
    rec.requestData(); // save what's buffered now, in case the tab closes while paused
    onChange();
  }

  function resume() {
    if (state() !== "paused") return;
    rec.resume();
    tap?.context.resume().catch(() => {});
    since = performance.now();
    onChange();
  }

  // Saves what's buffered now, so the stored recording runs up to this moment.
  async function flush() {
    if (state() === "inactive") return saving;
    await new Promise((resolve) => { flushed.push(resolve); rec.requestData(); });
  }

  async function stop() {
    if (state() === "inactive") return;
    const r = rec;
    if (r.state === "recording") activeMs += performance.now() - since;
    await new Promise((resolve) => { r.onstop = resolve; r.stop(); });
    stream.getTracks().forEach((t) => t.stop());
    tap?.context.close().catch(() => {});
    tap = null;
    rec = null;
    stream = null;
    const final = { ...clip, duration: activeMs / 1000 };
    clip = final;
    await saving;
    await run(["clips"], "readwrite", (tx) => { tx.objectStore("clips").put(final); }).catch(() => {});
    onChange();
  }

  // The recording being made now, or null.
  const clipId = () => (state() === "inactive" ? null : clip.id);
  // The record of the latest recording made here ({id, started_at, speech…}), or null.
  const current = () => clip;
  // The LiveAudio of a recording made on this page, if it's still held.
  const live = (id) => (audio?.clip === id && !audio.lost ? audio : null);

  return { start, pause, resume, stop, flush, state, seconds, clipId, current, live };
}
