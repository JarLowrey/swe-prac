// Basic checks of Java and C++ on the built site's javac and clang, that a solver's correct code
// works:
//
// * Correct solutions to a few problems (solutions/<language>/<problem id>.java or .cpp,
//   SPOILERS), each run against every test of its problem, hidden ones included, at the page's
//   time limits for that language. The problems are picked so that together they use every
//   argument and return type, adapter and answer comparison the problems have, so each part of
//   the generated harnesses (decoding the test values, encoding the results) and of judge.js is
//   checked against a right answer. When a new problem brings a shape none of them has, the
//   coverage test says so: add a solution to it.
// * The standard library and language features interview code uses (apis/Scratch.java and
//   apis/scratch.cpp, run as scratch files that check themselves), and the gaps the README
//   names, so it stays true.
//
// java.test.mjs and cpp.test.mjs check the rest: every starter builds and runs, crashes,
// compile errors and time limits.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { before, describe, test } from "node:test";

import { data, importSite, readSiteJson, toolchain } from "./harness.mjs";

const EXTENSIONS = { java: ".java", cpp: ".cpp" };
const LANGUAGES = Object.keys(EXTENSIONS);
const LAST_LEVEL = data.levels.at(-1);
const coding = new Map(data.problems.map((p) => [p.problem.id, p]));
const algo = new Map(data.algo.problems.map((p) => [p.problem.id, p]));

/** {problem id: code} for one language. */
function solutions(language) {
  const ext = EXTENSIONS[language];
  const dir = new URL(`./solutions/${language}/`, import.meta.url);
  return Object.fromEntries(readdirSync(dir).filter((f) => f.endsWith(ext)).sort()
    .map((f) => [f.slice(0, -ext.length), readFileSync(new URL(f, dir), "utf8")]));
}

// One compiler per language, shared by the describes below.
const toolchains = {};
const toolchainFor = (language) => (toolchains[language] ??= toolchain(language));

const trackOf = (id) => (algo.has(id) ? "algo" : coding.has(id) ? "coding" : null);
const failures = (ends) => ends.filter((e) => !e.passed).map((e) => `${e.id}: ${e.error ?? JSON.stringify(e.steps.find((s) => !s.ok))}`);

// -- shapes: what a problem's harness has to handle ---------------------------------------
function splitTopLevel(text) {
  const out = [];
  let depth = 0;
  let current = "";
  for (const ch of text) {
    if (ch === "<") depth++;
    if (ch === ">") depth--;
    if (ch === "," && depth === 0) {
      out.push(current.trim());
      current = "";
    } else {
      current += ch;
    }
  }
  if (current.trim()) out.push(current.trim());
  return out;
}

/** "public int[] twoSum(int[] nums, int target)" -> ["java returns int[]", "java takes int[]", ...] */
function signatureShapes(language, signature) {
  const [, ret, params] = signature.match(/^(?:public )?(.+?) \w+\((.*)\)$/);
  const types = splitTopLevel(params).map((p) => p.slice(0, p.lastIndexOf(" ")).replace(/^const /, "").replace(/&$/, ""));
  return [`${language} returns ${ret}`, ...types.map((t) => `${language} takes ${t}`)];
}

async function shapes(id) {
  const out = new Set();
  if (algo.has(id)) {
    const { options } = await readSiteJson(`tests/algo/${id}.json`);
    out.add(`compare ${options.compare ?? "exact"}`);
    const adapters = options.adapters ?? {};
    for (const kind of adapters.args ?? []) if (kind) out.add(`argument adapter ${kind}`);
    if (adapters.result) out.add(`result adapter ${adapters.result}`);
    if (adapters.check) out.add(`check ${adapters.check}`);
    for (const language of LANGUAGES) {
      for (const shape of signatureShapes(language, algo.get(id).langs[language].signature)) out.add(shape);
    }
  } else {
    for (const language of LANGUAGES) {
      const stubs = Object.values(coding.get(id).langs[language].stubs).join("\n");
      for (const [, signature] of stubs.matchAll(/^ {4}([^/\s].*\))\s*\{$/gm)) {
        for (const shape of signatureShapes(language, signature)) out.add(shape);
      }
    }
  }
  return out;
}

describe("the solutions", () => {
  test("are to real problems, the same ones in each language", () => {
    const ids = LANGUAGES.map((language) => Object.keys(solutions(language)));
    assert.deepEqual(ids[0].filter((id) => !trackOf(id)), [], "no such problem");
    for (const other of ids.slice(1)) assert.deepEqual(other, ids[0]);
  });

  test("together use every type, adapter and comparison the problems have", async () => {
    const where = new Map(); // shape -> the problems that have it
    for (const id of [...coding.keys(), ...algo.keys()]) {
      for (const shape of await shapes(id)) where.set(shape, [...(where.get(shape) ?? []), id]);
    }
    const covered = new Set();
    for (const id of Object.keys(solutions(LANGUAGES[0]))) for (const shape of await shapes(id)) covered.add(shape);
    const missing = [...where].filter(([shape]) => !covered.has(shape)).map(([shape, ids]) => `${shape}: ${ids.slice(0, 3).join(", ")}`);
    assert.deepEqual(missing, [], "add a solution to one of these problems");
  });
});

for (const language of LANGUAGES) {
  describe(`${language}: a correct solution passes every test`, () => {
    let tc;
    let scaleLimits;
    before(async () => {
      tc = await toolchainFor(language);
      ({ scaleLimits } = await importSite("compiled.js"));
    });

    for (const [id, code] of Object.entries(solutions(language))) {
      test(id, async () => {
        const track = trackOf(id);
        const file = await readSiteJson(`tests/${track}/${id}.json`);
        // Every level's tests, on the last level's harness, as a finished session submits them.
        const tests = scaleLimits(file.tests, language);
        const { build, ends } = await tc.tests(file, code, tests, track === "coding" ? LAST_LEVEL : null);
        assert.ok(build.ok, JSON.stringify(build.diagnostics.filter((d) => d.severity === "error")));
        assert.deepEqual(build.diagnostics.filter((d) => d.file === file.langs[language].file), [], "warnings");
        assert.deepEqual(failures(ends), []);
        assert.equal(ends.length, tests.length);
      });
    }
  });
}

// -- the standard library ------------------------------------------------------------------
const SCRATCH = { java: "Scratch.java", cpp: "scratch.cpp" };
// Gaps the README names, and the compiler's message for each.
const GAPS = {
  java: [["java.util.StringJoiner", 'String s = new java.util.StringJoiner(",").toString();', /cannot find symbol/]],
  cpp: [["exceptions", 'throw std::runtime_error("x");', /cannot use 'throw' with exceptions disabled/]],
};
const program = (language, body) => (language === "java"
  ? `public class Scratch {\n    public static void main(String[] args) {\n        ${body}\n    }\n}\n`
  : `#include <bits/stdc++.h>\nint main() {\n    ${body}\n}\n`);

for (const language of LANGUAGES) {
  describe(`${language}: the standard library`, () => {
    let tc;
    let file;
    let starter;
    before(async () => {
      tc = await toolchainFor(language);
      const twoSum = data.algo.problems.find((p) => p.problem.id.endsWith("two_sum"));
      file = await readSiteJson(`tests/algo/${twoSum.problem.id}.json`);
      starter = twoSum.langs[language].starter_code;
    });

    test("what interview code uses works", async () => {
      const code = readFileSync(new URL(`./apis/${SCRATCH[language]}`, import.meta.url), "utf8");
      const { build, out, exitCode } = await tc.scratch(file, starter, code);
      assert.ok(build.ok, JSON.stringify(build.diagnostics.filter((d) => d.severity === "error")));
      const lines = out.trimEnd().split("\n");
      assert.deepEqual(lines.filter((l) => l.startsWith("FAIL")), []);
      const ok = lines.filter((l) => l.startsWith("ok ")).length;
      assert.ok(ok > 40, `only ${ok} checks ran`);
      assert.equal(lines.at(-1), `${ok} passed, 0 failed`);
      assert.ok(lines.includes("printf 1 two"), "printf and the stream print in order");
      assert.equal(exitCode, 0);
    });

    for (const [name, body, message] of GAPS[language]) {
      test(`${name} doesn't compile, as the README says`, async () => {
        const build = await tc.compile({
          files: { ...file.langs[language].files, [file.langs[language].file]: starter, [SCRATCH[language]]: program(language, body) },
          main: language === "java" ? "Scratch" : SCRATCH[language],
          mode: "check",
        });
        assert.equal(build.ok, false);
        assert.match(build.diagnostics.map((d) => d.message).join("\n"), message);
      });
    }
  });
}
