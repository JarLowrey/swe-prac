// Running one compiled Java or C++ program: the tests (Run and Submit) or the scratch file.
// lang-run.js does it in a Web Worker that's thrown away afterwards; tests/js/ does it in Node.
// It posts the messages py-job.js does for Python:
//
//   {type: "begin"}                       the program starts
//   {type: "event", event}                a runner event (start, call, end, stopped, done)
//   {type: "stdout" | "stderr", text}     scratch output, as it's printed
//   {type: "finished", exit_code}         the job ended (exit_code for scratch)
//   {type: "fatal", message}              the program couldn't run at all
//
// A Java NullPointerException, an array index out of range or a stack overflow isn't an exception
// the program can catch here: WebAssembly stops the program (a "trap"). The same goes for a C++
// crash. The test that was running fails with what happened, and the program starts again, in a
// fresh instance, from the next test.
import { Judge } from "./judge.js";
import { WasiExit, createWasi } from "./wasi.js";

const MAX_SCRATCH_CHARS = 50000;
const JAVA_SCRATCH_EXIT = "swe-scratch-exit-1"; // SweScratch.EXIT

const STACK = "the recursion went too deep for the browser's stack (a few thousand calls at most). Use a loop, or an explicit stack.";
const NO_CATCH = "In the browser this stops the test: it can't be caught.";

/** What a Java trap means, as the exception the JVM would have thrown. */
export function javaCrash(err) {
  const m = String(err?.message ?? err);
  if (/stack size|call stack|too much recursion/i.test(m)) return `java.lang.StackOverflowError: ${STACK}`;
  if (/null/i.test(m)) return `java.lang.NullPointerException: your code used a null reference. ${NO_CATCH}`;
  if (/out of bounds|index/i.test(m)) return `java.lang.ArrayIndexOutOfBoundsException: an array index is out of range. ${NO_CATCH}`;
  if (/cast/i.test(m)) return `java.lang.ClassCastException. ${NO_CATCH}`;
  if (/divi.* by zero/i.test(m)) return "java.lang.ArithmeticException: / by zero";
  if (/memory/i.test(m)) return "java.lang.OutOfMemoryError";
  return m;
}

/** What a C++ trap means; `output` is what the program printed (libc++ explains its checks). */
export function cppCrash(err, output = "") {
  const m = String(err?.message ?? err);
  const check = /libc\+\+ Hardening assertion .* failed: (.*)/.exec(output);
  if (check) return `A standard library check failed: ${check[1].trim()}.`;
  const thrown = /(\w+) was thrown in -fno-exceptions mode with message "(.*)"/.exec(output);
  if (thrown) return `std::${thrown[1]} (${thrown[2]}): exceptions are off here, so it ends the test.`;
  if (/stack size|call stack|too much recursion|stack overflow/i.test(m)) return `Stack overflow: ${STACK}`;
  if (/unreachable/i.test(m)) return "The program aborted (abort(), assert, or a failed check).";
  if (/out of bounds/i.test(m)) return "Memory access out of bounds: an index past the end of an array, or a bad pointer.";
  if (/divi.* by zero/i.test(m)) return "Integer division by zero.";
  if (/integer overflow/i.test(m)) return "Integer overflow in a division (the minimum value divided by -1).";
  return `The program crashed: ${m}`;
}

const encoder = new TextEncoder();

// ---------------------------------------------------------------------------- Java (TeaVM)
async function startJava(load, wasm, { stdin, stdout, stderr }) {
  return load(wasm, {
    installImports(imports) {
      imports.teavmConsole.readStdin = stdin;
      imports.teavmConsole.putcharStdout = (c) => stdout(c & 0xffff);
      imports.teavmConsole.putcharStderr = (c) => stderr(c & 0xffff);
    },
  });
}

// stdin for the Java harness, read a byte at a time: the tests, then a verdict after each step.
function byteQueue(first) {
  const chunks = [first];
  let pos = 0;
  return {
    read() {
      while (chunks.length && pos >= chunks[0].length) {
        chunks.shift();
        pos = 0;
      }
      return chunks.length ? chunks[0][pos++] : -1;
    },
    push(text) {
      chunks.push(encoder.encode(text));
    },
  };
}

async function javaTests(job, judge, load) {
  let from = 0;
  for (;;) {
    const input = byteQueue(encoder.encode(judge.input(from)));
    let line = "";
    const program = await startJava(load, job.wasm, {
      stdin: input.read,
      stdout: (c) => {
        if (c !== 10) {
          line += String.fromCharCode(c);
          return;
        }
        const event = JSON.parse(line);
        line = "";
        const go = judge.onEvent(event);
        if (event.e === "step") input.push(go ? "1\n" : "0\n");
      },
      stderr: (c) => judge.onOutput(String.fromCharCode(c)),
    });
    try {
      program.exports.main([]);
      return;
    } catch (err) {
      if (!judge.current) throw err;
      const error = javaCrash(err);
      const type = error.split(":")[0].split(".").pop();
      if (!judge.crash(error, `<raised ${type}>`)) {
        judge.post({ event: "done" });
        return;
      }
      from = judge.next;
    }
  }
}

async function javaScratch(job, load, out) {
  const program = await startJava(load, job.wasm, {
    stdin: () => -1,
    stdout: (c) => out.write("stdout", String.fromCharCode(c)),
    stderr: (c) => out.write("stderr", String.fromCharCode(c)),
  });
  try {
    program.exports.main([]);
    return 0;
  } catch (err) {
    // SweScratch.java printed an uncaught exception already; anything else is a trap.
    if (!String(err?.message).includes(JAVA_SCRATCH_EXIT)) {
      out.write("stderr", `Exception in thread "main" ${javaCrash(err)}\n`);
    }
    return 1;
  }
}

// ---------------------------------------------------------------------------- C++ (WASI)
async function startCpp(module, { stdin, stdout, stderr, emit }) {
  let memory = null;
  const wasi = createWasi({ stdin, stdout, stderr });
  const decoder = new TextDecoder();
  const extra = emit ? { swe: { emit: (ptr, len) => emit(decoder.decode(new Uint8Array(memory.buffer, ptr, len))) } } : {};
  const instance = await WebAssembly.instantiate(module, wasi.imports(module, extra));
  memory = instance.exports.memory;
  wasi.setMemory(memory);
  return instance;
}

async function cppTests(job, judge) {
  const module = await WebAssembly.compile(job.wasm);
  let from = 0;
  for (;;) {
    const decoder = new TextDecoder();
    const output = (bytes) => judge.onOutput(decoder.decode(bytes, { stream: true }));
    const instance = await startCpp(module, {
      stdin: encoder.encode(judge.input(from)),
      stdout: output,
      stderr: output,
      emit: (text) => (judge.onEvent(JSON.parse(text)) ? 1 : 0),
    });
    let error;
    try {
      instance.exports._start();
      return;
    } catch (err) {
      if (err instanceof WasiExit && !judge.current) return; // main returned
      if (!judge.current) throw err;
      error = err instanceof WasiExit ? `The program called exit(${err.code}).` : cppCrash(err, judge.current.stdout);
    }
    if (!judge.crash(error)) {
      judge.post({ event: "done" });
      return;
    }
    from = judge.next;
  }
}

async function cppScratch(job, out) {
  const module = await WebAssembly.compile(job.wasm);
  const decoders = { stdout: new TextDecoder(), stderr: new TextDecoder() };
  let printed = "";
  const sink = (stream) => (bytes) => {
    const text = decoders[stream].decode(bytes, { stream: true });
    printed = (printed + text).slice(-2000);
    out.write(stream, text);
  };
  const instance = await startCpp(module, { stdout: sink("stdout"), stderr: sink("stderr") });
  try {
    instance.exports._start();
    return 0;
  } catch (err) {
    if (err instanceof WasiExit) return err.code;
    out.write("stderr", `\n${cppCrash(err, printed)}\n`);
    return 1;
  }
}

// ---------------------------------------------------------------------------- the job
// Scratch output reaches the page in batches (at most every 50 ms), up to MAX_SCRATCH_CHARS.
function scratchOutput(post) {
  let left = MAX_SCRATCH_CHARS;
  const pending = { stdout: "", stderr: "" };
  let flushed = performance.now();
  const flush = () => {
    for (const stream of ["stdout", "stderr"]) {
      if (pending[stream]) post({ type: stream, text: pending[stream] });
      pending[stream] = "";
    }
    flushed = performance.now();
  };
  return {
    write(stream, text) {
      if (left <= 0 || !text) return;
      const chunk = text.slice(0, left);
      left -= chunk.length;
      pending[stream] += chunk;
      if (performance.now() - flushed > 50) flush();
    },
    flush,
  };
}

/**
 * Run `job`: {kind: "tests" | "scratch", lang: "java" | "cpp", wasm, tests, options, names}.
 * `loadJava` is TeaVM's loader (vendor/java/compiler.wasm-runtime.js), for Java jobs.
 */
export async function runJob(job, post, { loadJava } = {}) {
  try {
    post({ type: "begin" });
    if (job.kind === "tests") {
      const judge = new Judge({
        tests: job.tests,
        options: job.options,
        names: job.names,
        post: (event) => post({ type: "event", event }),
      });
      if (job.lang === "java") await javaTests(job, judge, loadJava);
      else await cppTests(job, judge);
      post({ type: "finished", exit_code: 0 });
    } else {
      const out = scratchOutput(post);
      const code = job.lang === "java" ? await javaScratch(job, loadJava, out) : await cppScratch(job, out);
      out.flush();
      post({ type: "finished", exit_code: code });
    }
  } catch (err) {
    post({ type: "fatal", message: String(err?.message ?? err) });
  }
}
