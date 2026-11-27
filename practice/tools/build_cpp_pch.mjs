// Precompile the C++ standard headers for the browser's compiler, so a compile in the app takes a
// second or two instead of ten or more. tools/build_static.py runs this (Node 22 or newer):
//
//   node tools/build_cpp_pch.mjs <@yowasp/clang's gen/bundle.js> <out.pch>
//
// The header is swe_prac/static/lang/cpp/include/bits/stdc++.h, compiled with the flags the app
// compiles with (CPP_FLAGS in swe_prac/static/compilers.js): clang refuses a precompiled header
// built with other flags.
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const staticDir = path.join(here, "..", "swe_prac", "static");
const [bundle, out] = process.argv.slice(2);
if (!bundle || !out) {
  console.error("usage: node tools/build_cpp_pch.mjs <clang bundle.js> <out.pch>");
  process.exit(2);
}

const { CPP_FLAGS } = await import(pathToFileURL(path.join(staticDir, "compilers.js")).href);
const clang = await import(pathToFileURL(path.resolve(bundle)).href);
const header = await readFile(path.join(staticDir, "lang", "cpp", "include", "bits", "stdc++.h"), "utf8");
let stderr = "";
const decoder = new TextDecoder();
try {
  await clang.runClang(null, {}, { fetchProgress: () => {} }); // load clang's files, quietly
  const files = await clang.runClang(
    ["clang++", ...CPP_FLAGS, "-x", "c++-header", "all.h", "-o", "all.h.pch"],
    { "all.h": "#include <bits/stdc++.h>\n", include: { bits: { "stdc++.h": header } } },
    {
      stderr: (bytes) => { if (bytes) stderr += decoder.decode(bytes, { stream: true }); },
    },
  );
  await writeFile(out, files["all.h.pch"]);
} catch (err) {
  console.error(stderr || err);
  process.exit(1);
}
