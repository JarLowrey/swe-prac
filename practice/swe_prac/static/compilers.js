// Compiling Java and C++ to WebAssembly in the browser. lang-compile.js runs these in a Web
// Worker; tests/js/ runs them in Node. Both take their files through `fetchBytes(path)` and
// `fetchText(path)`, paths relative to the site (vendor/java/compiler.wasm, lang/cpp/swe.hpp).
//
// compile({files, main, mode}) -> {ok, wasm, diagnostics, ms}
//   files        {name: text}: the solution and the job's other sources (harness or scratch)
//   main         Java: the main class; C++: the file to compile (it includes the rest)
//   mode         "build" (compile and link) or "check" (diagnostics only, faster)
//   diagnostics  [{file, line, col, severity: "error" | "warning", message}]
//
// Java: javac and TeaVM (WebAssembly GC), from @live-codes/java-wasm. C++: clang and wasm-ld
// (LLVM, wasm32-wasip1), from @yowasp/clang, with the standard headers precompiled at build time
// (lang/cpp/all.h.pch, see tools/build_cpp_pch.mjs) so a compile takes a second or two.

/** The Java sources every job compiles with the solution (static/lang/java/). */
export const JAVA_RUNTIME = ["SweJson.java", "SweRun.java", "SweAdapterError.java"];
// A scratch job (main "Scratch") runs through this, which reports an uncaught exception.
const JAVA_SCRATCH = "SweScratch.java";

/** The C++ flags; the precompiled header was built with the same ones (tools/build_cpp_pch.mjs). */
export const CPP_FLAGS = [
  "-std=c++20",
  "-O2",
  "-fno-exceptions", // this WebAssembly target has no C++ exceptions
  "-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_DEBUG", // a bad index stops with a message
  "-I",
  "include",
];
const CPP_LINK = ["-Wl,-z,stack-size=8388608"]; // 8 MB of stack for recursion
const CPP_WARNINGS = ["-Wall", "-Wno-unused-variable", "-Wno-unused-but-set-variable", "-Wno-sign-compare"];

const elapsed = (t0) => Math.round(performance.now() - t0);

// -------------------------------------------------------------------------------- Java
export async function createJavaCompiler({ load, fetchBytes, fetchText }) {
  const [teavm, sdk, classlib, ...runtime] = await Promise.all([
    load(await fetchBytes("vendor/java/compiler.wasm")),
    fetchBytes("vendor/java/compile-classlib-teavm.bin"),
    fetchBytes("vendor/java/runtime-classlib-teavm.bin"),
    ...[...JAVA_RUNTIME, JAVA_SCRATCH].map((name) => fetchText(`lang/java/${name}`)),
  ]);
  const compiler = teavm.exports.createCompiler();
  compiler.setSdk(new Int8Array(sdk.buffer, sdk.byteOffset, sdk.byteLength));
  compiler.setTeaVMClasslib(new Int8Array(classlib.buffer, classlib.byteOffset, classlib.byteLength));
  let diagnostics = [];
  compiler.onDiagnostic((d) => {
    const severity = String(d.severity).toLowerCase();
    if (severity !== "error" && severity !== "warning") return;
    diagnostics.push({
      file: d.fileName ? String(d.fileName) : null,
      line: Number(d.lineNumber) || null,
      col: Number(d.columnNumber) || null,
      severity,
      message: String(d.message ?? ""),
    });
  });
  const runtimeFiles = Object.fromEntries(JAVA_RUNTIME.map((name, i) => [name, runtime[i]]));
  const scratchLauncher = runtime[JAVA_RUNTIME.length];

  return {
    compile({ files, main, mode = "build" }) {
      const t0 = performance.now();
      diagnostics = [];
      const scratch = main === "Scratch";
      const sources = { ...runtimeFiles, ...(scratch ? { [JAVA_SCRATCH]: scratchLauncher } : {}), ...files };
      compiler.clearSourceFiles();
      for (const [name, text] of Object.entries(sources)) compiler.addSourceFile(name, text);
      const compiled = compiler.compile();
      const done = (ok, wasm = null) => ({ ok, wasm, diagnostics: diagnostics.filter((d) => d.severity === "error" || !d.file?.startsWith("Swe")), ms: elapsed(t0) });
      if (!compiled || mode === "check") return done(compiled);
      const generated = compiler.generateWebAssembly({
        outputName: "app",
        mainClass: scratch ? "SweScratch" : main,
        optimizationLevel: "SIMPLE",
      });
      const wasm = generated ? compiler.getWebAssemblyOutputFile("app.wasm") : null;
      if (!wasm) {
        if (!diagnostics.some((d) => d.severity === "error")) {
          diagnostics.push({ file: null, line: null, col: null, severity: "error", message: "The Java compiler couldn't build this program." });
        }
        return done(false);
      }
      return done(true, new Uint8Array(wasm.buffer, wasm.byteOffset, wasm.byteLength).slice());
    },
  };
}

// -------------------------------------------------------------------------------- C++
const CPP_DIAGNOSTIC = /^([^\s:][^:]*):(\d+):(\d+): (fatal error|error|warning): (.*)$/;

/** clang's stderr as diagnostics (notes and the source excerpts are folded into the message). */
export function parseClang(text) {
  const out = [];
  let last = null;
  for (const line of text.split("\n")) {
    const m = CPP_DIAGNOSTIC.exec(line);
    if (m) {
      last = {
        file: m[1].replace(/^\.\//, ""),
        line: Number(m[2]),
        col: Number(m[3]),
        severity: m[4] === "warning" ? "warning" : "error",
        message: m[5],
      };
      out.push(last);
    } else if (/^\S+:\d+:\d+: note: /.test(line) && last) {
      last.message += `\n${line.replace(/^\S+:\d+:\d+: /, "")}`;
    }
  }
  if (!out.length && /\berror\b/.test(text)) {
    out.push({ file: null, line: null, col: null, severity: "error", message: text.trim() });
  }
  return out;
}

export async function createCppCompiler({ clang, fetchBytes, fetchText }) {
  const [pch, stdcpp, swe, helpers] = await Promise.all([
    fetchBytes("lang/cpp/all.h.pch"),
    fetchText("lang/cpp/include/bits/stdc++.h"),
    fetchText("lang/cpp/swe.hpp"),
    fetchText("lang/cpp/helpers.hpp"),
  ]);
  const shared = {
    "all.h": "#include <bits/stdc++.h>\n",
    "all.h.pch": pch,
    include: { bits: { "stdc++.h": stdcpp } },
    "swe.hpp": swe,
    "helpers.hpp": helpers,
  };
  const decoder = new TextDecoder();

  return {
    async compile({ files, main, mode = "build" }) {
      const t0 = performance.now();
      let stderr = "";
      const args = [
        "clang++", ...CPP_FLAGS, ...CPP_WARNINGS, "-fno-color-diagnostics",
        "-include-pch", "all.h.pch", "-include", "swe_nodes.hpp", main,
        ...(mode === "check" ? ["-fsyntax-only"] : ["-o", "out.wasm", ...CPP_LINK]),
      ];
      let out = null;
      try {
        out = await clang.runClang(args, { ...shared, ...files }, {
          stderr: (bytes) => { if (bytes) stderr += decoder.decode(bytes, { stream: true }); },
        });
      } catch (err) {
        if (!("code" in err)) throw err; // not a compile error: the compiler itself failed
      }
      const diagnostics = parseClang(stderr);
      const wasm = out?.["out.wasm"] ?? null;
      const ok = out !== null && (mode === "check" || wasm !== null);
      return { ok, wasm: ok && wasm ? new Uint8Array(wasm) : null, diagnostics, ms: elapsed(t0) };
    },
  };
}
