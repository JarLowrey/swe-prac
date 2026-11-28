// Speech to text for the design interviewer: the session's recordings, transcribed in this
// browser with Whisper (asr-worker.js), so the AI interviewer knows what the candidate said. The
// audio is never uploaded. The model downloads from the Hugging Face Hub once, and the browser
// keeps it.
//
// The model loads when Record is pressed, and the recording is transcribed in the background as
// it's made. Whisper hears at most 30 s at a time, so the audio goes to it in pieces, each cut at
// a quiet moment so that no word is split, and each finished piece is saved beside the recording
// (recorder.js). While recording, the pieces are short and done every few seconds, so when the
// candidate asks for a hint only the last few seconds are left to transcribe. The background
// works from the recorder's live samples; a recording left unfinished by a reload is decoded
// from its saved file.
//
// No DOM at import time: tests/js/ imports pieces, cleanText and transcriptLines in Node.

import { clipBlob, getTranscript, listClips, putTranscript } from "./recorder.js";

// The speech models to pick from when recording starts: English-only Whisper, its 8-bit
// weights, each pinned to a revision of its model repo. params: millions of parameters; mb: the
// whole download (weights, tokenizer and config) in MB. A recording keeps the one it was started
// with (its clip's `speech`), and its saved transcript says which made it.
export const MODELS = {
  fast: {
    name: "Small and fast", label: "Whisper tiny.en", id: "onnx-community/whisper-tiny.en",
    revision: "794207fec2761281fe63a23a94b7e9f53a4efbc1", params: 39, mb: 44,
  },
  accurate: {
    name: "Large and accurate", label: "Whisper base.en", id: "onnx-community/whisper-base.en",
    revision: "51eefc0af78b103839eda9e7e4f4186acc6517fe", params: 74, mb: 80,
  },
};
export const DEFAULT_SPEECH = "accurate";

// Transformers.js keeps every file it downloads in the browser's Cache Storage, under this
// name, keyed by the file's Hub URL, so a model downloads once and then loads from the browser.
// The weights are most of the download: the files asr-worker.js's 8-bit (q8) weights come from.
const CACHE = "transformers-cache";
const WEIGHTS = ["onnx/encoder_model_quantized.onnx", "onnx/decoder_model_merged_quantized.onnx"];
export const weightUrls = (model) => WEIGHTS.map((file) => `https://huggingface.co/${model.id}/resolve/${model.revision}/${file}`);

// Whether this browser already has the model, so it loads without a download. False when it
// can't tell.
export async function modelSaved(model) {
  try {
    const found = await Promise.all(weightUrls(model).map((url) => globalThis.caches.match(url, { cacheName: CACHE })));
    return found.every(Boolean);
  } catch {
    return false;
  }
}

// The model for a recording: the one its transcript was started with, else the one picked when
// it was recorded, else the default (recordings from before there was a choice).
export function clipModel(clip, saved = null) {
  const all = Object.values(MODELS);
  return all.find((m) => m.id === saved?.model) ?? MODELS[clip?.speech] ?? MODELS[DEFAULT_SPEECH];
}
export const RATE = 16000; // what Whisper takes
// A piece is cut at the quietest 0.1 s between min and max seconds in. Whole recordings go in
// long pieces (fewer passes of Whisper, which costs about 3 s however short the piece is); the
// recording being made goes in short ones, so a prompt is left with only a few seconds to do.
const LONG = { min: 20, max: 30 };
const LIVE = { min: 6, max: 12 };
const SILENCE = 0.003; // RMS: a piece with no 0.1 s louder than this has no speech in it
const MIN_SPEECH = 0.3; // seconds
const EVERY = 3000; // ms between background passes while recording
const BACKOFF = 60000; // ms the background rests after a pass fails

export const transcriptionSupported = () => Boolean(globalThis.Worker && globalThis.OfflineAudioContext && globalThis.WebAssembly);

function rms(samples, start, end) {
  let sum = 0;
  for (let i = start; i < end; i++) sum += samples[i] * samples[i];
  return Math.sqrt(sum / Math.max(1, end - start));
}

// [start, end) sample ranges covering samples[from:]: at most `max` seconds each, each cut in the
// middle of the quietest 0.1 s between `min` and `max` seconds in. The last one ends with the audio.
export function pieces(samples, from = 0, { min, max } = LONG, rate = RATE) {
  const frame = Math.round(rate / 10);
  const out = [];
  let start = Math.max(0, from);
  while (samples.length - start > max * rate) {
    let cut = start + max * rate;
    let quietest = Infinity;
    for (let at = start + min * rate; at + frame <= start + max * rate; at += frame) {
      const level = rms(samples, at, at + frame);
      if (level < quietest) { quietest = level; cut = at + Math.floor(frame / 2); }
    }
    out.push([start, cut]);
    start = cut;
  }
  if (samples.length > start) out.push([start, samples.length]);
  return out;
}

function heard(samples, start, end, rate = RATE) {
  if (end - start < MIN_SPEECH * rate) return false;
  const frame = Math.round(rate / 10);
  for (let at = start; at < end; at += frame) if (rms(samples, at, Math.min(end, at + frame)) >= SILENCE) return true;
  return false;
}

// Whisper's text without the tags it writes for sounds that aren't speech, [BLANK_AUDIO] or
// (music), and "" when no word is left (it sometimes writes a lone ".").
export function cleanText(text) {
  const clean = String(text ?? "").replace(/[[(][^\])]*[\])]/g, " ").replace(/\s+/g, " ").trim();
  return /[\p{L}\p{N}]/u.test(clean) ? clean : "";
}

// Whisper's segments for one piece, in seconds from the start of the recording.
function segmentsOf(chunks, offset, length) {
  const round = (s) => Math.round(s * 100) / 100;
  return chunks.map((c) => {
    const [start, end] = c.timestamp ?? [];
    return { start: round(offset + (start ?? 0)), end: round(offset + (end ?? length)), text: cleanText(c.text) };
  }).filter((s) => s.text);
}

// The prompt's transcript, [{at, text}] in session time: every recording's segments, in order.
// clips: [{id, started_at}]; transcripts: Map of clip id -> {segments}.
export function transcriptLines(clips, transcripts) {
  return clips.flatMap((clip) => (transcripts.get(clip.id)?.segments ?? [])
    .map((s) => ({ at: clip.started_at + s.start, text: s.text })));
}

// ---------------------------------------------------------------- audio
// A saved recording as 16 kHz mono samples: the browser decodes and resamples it.
async function decode(blob) {
  if (!blob.size) return new Float32Array(0);
  let audio;
  try {
    audio = await new OfflineAudioContext(1, 1, RATE).decodeAudioData(await blob.arrayBuffer());
  } catch {
    throw new Error("This browser couldn't read the recording.");
  }
  if (audio.numberOfChannels === 1) return audio.getChannelData(0);
  const mono = new Float32Array(audio.length);
  for (let c = 0; c < audio.numberOfChannels; c++) {
    const channel = audio.getChannelData(c);
    for (let i = 0; i < mono.length; i++) mono[i] += channel[i] / audio.numberOfChannels;
  }
  return mono;
}

// Live samples at the microphone's rate, resampled to 16 kHz by the browser.
async function resample(samples, rate) {
  if (rate === RATE || !samples.length) return samples;
  const context = new OfflineAudioContext(1, Math.max(1, Math.round((samples.length * RATE) / rate)), RATE);
  const buffer = context.createBuffer(1, samples.length, rate);
  buffer.copyToChannel(samples, 0);
  const source = context.createBufferSource();
  source.buffer = buffer;
  source.connect(context.destination);
  source.start();
  return (await context.startRendering()).getChannelData(0);
}

function jobError({ phase, message }) {
  if (phase === "run") return `Transcription failed: ${message}`;
  return /fetch|network|load failed/i.test(message)
    ? "Couldn't download the speech model. Check your connection."
    : `The speech model didn't load: ${message}`;
}

// ---------------------------------------------------------------- the transcriber
// One per session page. recorder: the page's, or null. While a recording runs it transcribes in
// the background; transcript() brings it up to now for a prompt. stop() ends it all.
export function createTranscriber({ sessionId, recorder = null }) {
  let worker = null;
  const jobs = new Map(); // id -> {resolve, reject, onLoad}
  let lastJob = 0;
  let queue = Promise.resolve(); // one pass at a time
  let waiting = 0; // prompts waiting their turn: the background gives way to them
  let busy = false; // a background pass is queued or running
  let restUntil = 0;
  let stopped = false;

  function failAll(message) {
    for (const job of jobs.values()) job.reject(new Error(message));
    jobs.clear();
  }

  function startWorker() {
    worker = new Worker(new URL("asr-worker.js", import.meta.url), { type: "module" });
    worker.onmessage = ({ data }) => {
      const job = jobs.get(data.id);
      if (!job) return;
      if (data.type === "load") { job.onLoad(data.loaded, data.total); return; }
      jobs.delete(data.id);
      if (data.type === "done") job.resolve(data.chunks);
      else job.reject(new Error(jobError(data)));
    };
    worker.onerror = (e) => {
      e.preventDefault?.();
      worker.terminate();
      worker = null;
      failAll("The speech model didn't start. Reload the page and try again.");
    };
  }

  // Whisper's segments for up to 30 s of audio (its buffer moves to the worker). No audio: just
  // load the model.
  function whisper(audio, model, onLoad = () => {}) {
    if (stopped) return Promise.reject(new Error("Stopped."));
    if (!worker) startWorker();
    return new Promise((resolve, reject) => {
      const id = ++lastJob;
      jobs.set(id, { resolve, reject, onLoad });
      worker.postMessage({ id, model: model.id, revision: model.revision, audio }, audio ? [audio.buffer] : []);
    });
  }

  // One pass over the session's recordings: [{at, text}] up to now, or null with none. The
  // background's pass (ahead) only does finished pieces of the recording being made, and only
  // from its live samples (decoding the file every few seconds would be too heavy), and it stops
  // between pieces when a prompt is waiting.
  async function pass({ ahead = false, onProgress = () => {} } = {}) {
    const liveId = recorder?.clipId() ?? null;
    if (!ahead && liveId && !recorder.live(liveId)) await recorder.flush(); // the file runs up to now
    const clips = await listClips(sessionId);
    if (!clips.length) return null;

    const transcripts = new Map();
    for (const clip of clips) {
      const saved = await getTranscript(clip.id);
      const model = clipModel(clip, saved);
      transcripts.set(clip.id, saved?.model === model.id ? saved
        : { clip: clip.id, model: model.id, upto: 0, done: false, segments: [] });
    }
    const todo = clips.filter((c) => !transcripts.get(c.id).done);
    const length = (c) => recorder?.live(c.id)?.seconds ?? c.duration;
    const total = todo.reduce((sum, c) => sum + Math.max(0, length(c) - transcripts.get(c.id).upto), 0);
    let done = 0;
    const giveWay = () => stopped || (ahead && waiting > 0);

    for (const clip of todo) {
      if (giveWay()) break;
      const t = transcripts.get(clip.id);
      const model = clipModel(clip, t);
      const onLoad = (loaded, size) => onProgress({ phase: "load", loaded, total: size, mb: model.mb });
      const ongoing = clip.id === liveId;
      const live = recorder?.live(clip.id) ?? null;
      if (ahead && ongoing && !(live && live.seconds - t.upto > LIVE.max)) continue; // no finished piece yet
      const raw = live?.from(t.upto);
      const samples = raw ? await resample(raw, live.rate)
        : (await decode(await clipBlob(clip))).subarray(Math.round(t.upto * RATE));
      const origin = t.upto; // samples[0], in seconds from the start of the recording
      const parts = pieces(samples, 0, ahead && ongoing ? LIVE : LONG); // a prompt's: as few as can be
      const tail = []; // the piece still being spoken: in this prompt, not saved
      let finished = true;
      for (const [i, [start, end]] of parts.entries()) {
        const last = i === parts.length - 1;
        if ((ahead && ongoing && last) || giveWay()) { finished = false; break; }
        const segments = heard(samples, start, end)
          ? segmentsOf(await whisper(samples.slice(start, end), model, onLoad), origin + start / RATE, (end - start) / RATE) : [];
        done += (end - start) / RATE;
        onProgress({ phase: "transcribe", done: Math.min(done, total), total });
        if (ongoing && last) {
          tail.push(...segments);
        } else {
          t.segments.push(...segments);
          t.upto = origin + end / RATE;
          await putTranscript(t);
          live?.release(t.upto);
        }
      }
      if (finished && !ongoing && !t.done) {
        t.done = true;
        await putTranscript(t);
      }
      transcripts.set(clip.id, { ...t, segments: [...t.segments, ...tail] });
    }
    return transcriptLines(clips, transcripts);
  }

  let again = false; // asked for while a pass ran: one more after it
  async function background() {
    if (busy) { again = true; return; }
    if (stopped || waiting || Date.now() < restUntil) return;
    busy = true;
    const run = queue.then(() => pass({ ahead: true }));
    queue = run.catch(() => {});
    try {
      await run;
    } catch (err) {
      if (!stopped) {
        restUntil = Date.now() + BACKOFF;
        console.warn(`Transcribing in the background stopped for a minute: ${err.message}`);
      }
    } finally {
      busy = false;
      if (again) { again = false; background(); }
    }
  }
  const timer = recorder ? setInterval(() => { if (recorder.state() === "recording") background(); }, EVERY) : null;
  const first = setTimeout(background, 2000); // a recording left unfinished by a reload

  return {
    // What was said in the session's recordings: [{at, text}] at session times, [] when nothing
    // was heard, null when the session has no recording. onProgress gets {phase: "load", loaded,
    // total, mb} (bytes of the model) and {phase: "transcribe", done, total} (seconds of audio).
    transcript({ onProgress = () => {} } = {}) {
      waiting++;
      const run = queue.then(() => { waiting--; return pass({ onProgress }); });
      queue = run.catch(() => {});
      return run;
    },
    // Loads a speech model, so the recording about to start is transcribed without a wait. It
    // stays loaded for the page. Resolves once it's ready; onLoad gets (loaded, total) bytes of
    // the model as they come, from the Hub the first time and from the browser after that.
    load(model, onLoad = () => {}) {
      return whisper(null, model, onLoad).then(() => {});
    },
    // The recorder's onChange: a recording that stops is finished in the background.
    recordingChanged() {
      if (recorder?.state() === "inactive") background();
    },
    stop() {
      stopped = true;
      clearInterval(timer);
      clearTimeout(first);
      worker?.terminate();
      worker = null;
      failAll("Stopped.");
    },
  };
}
