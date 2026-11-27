// The tests java.test.mjs and cpp.test.mjs share: the same checks of each compiled language, on
// the built site's toolchains (harness.mjs's toolchain()). Two files so Node runs them at once.
import assert from "node:assert/strict";
import { before, describe, test } from "node:test";

import { data, importSite, readSiteJson, toolchain } from "./harness.mjs";

const TWO_SUM = data.algo.problems.find((p) => p.problem.id.endsWith("two_sum")).problem.id;
const FILE_STORE = data.problems.find((p) => p.problem.id.endsWith("file_store")).problem.id;

// Each starter level is the starter with the stubs of levels 2..level pasted in at the end of
// the class, as the statement's "Insert at cursor" would.
function withStubs(starter, stubs, level) {
  let code = starter;
  for (let lv = 2; lv <= level; lv++) {
    const close = code.lastIndexOf("}");
    code = `${code.slice(0, close).replace(/\s*$/, "\n")}\n${stubs[String(lv)]}${code.slice(close)}`;
  }
  return code;
}

const failures = (ends) => ends.filter((e) => !e.passed).map((e) => `${e.id}: ${e.error ?? JSON.stringify(e.steps.find((s) => !s.ok))}`);

/**
 * `solutions`: code in this language for
 *   twoSum        a correct Two Sum that prints "n=<length>"
 *   twoSumNaive   a correct Two Sum with two nested loops: too slow on the large tests
 *   twoSumBroken  Two Sum that crashes (a trap) when nums has 4 numbers, else is correct
 *   twoSumThrows  Two Sum whose first example fails some other way, else is correct
 *   fileStore     File Store's level 1
 *   syntaxError   Two Sum that doesn't compile (an error on line 3)
 *   renamed       Two Sum with the method renamed, so the tests' calls don't compile
 * `crash`: a pattern the crashed test's error matches. `thrown`: the same for twoSumThrows.
 */
export function compiledSuite(language, { solutions, crash, thrown, starterError }) {
  let tc;
  let twoSum;
  let fileStore;
  before(async () => {
    tc = await toolchain(language);
    twoSum = await readSiteJson(`tests/algo/${TWO_SUM}.json`);
    fileStore = await readSiteJson(`tests/coding/${FILE_STORE}.json`);
  });

  describe(`${language}: running solutions`, () => {
    test("a correct solution passes every test, and each test keeps its own output", async () => {
      const { build, ends, events } = await tc.tests(twoSum, solutions.twoSum, twoSum.tests);
      assert.ok(build.ok, JSON.stringify(build.diagnostics));
      assert.deepEqual(failures(ends), []);
      assert.deepEqual(ends.map((e) => e.id), twoSum.tests.map((t) => t.id));
      const first = ends[0];
      assert.equal(first.stdout, `n=${twoSum.tests[0].steps[0].args[0].length}\n`);
      assert.equal(events.at(-1).event, "done");
    });

    test("a coding problem's level runs its calls in order on one object per test", async () => {
      const tests = fileStore.tests.filter((t) => t.level === 1);
      const { build, ends } = await tc.tests(fileStore, solutions.fileStore, tests, 1);
      assert.ok(build.ok, JSON.stringify(build.diagnostics));
      assert.deepEqual(failures(ends), []);
      assert.equal(ends.length, tests.length);
      assert.equal(ends[0].steps.length, tests[0].steps.length);
      assert.equal(ends[0].steps[0].call, data.problems.find((p) => p.problem.id === FILE_STORE).langs[language].names[tests[0].steps[0].call]);
    });

    test("a crash fails its own test only: the program starts again from the next", async () => {
      const shown = twoSum.tests.filter((t) => t.visibility === "shown");
      const crashing = shown.filter((t) => t.steps[0].args[0].length === 4).map((t) => t.id);
      assert.ok(crashing.length && crashing.length < shown.length);
      const { ends, events } = await tc.tests(twoSum, solutions.twoSumBroken, shown);
      assert.equal(ends.length, shown.length);
      for (const end of ends) {
        if (crashing.includes(end.id)) {
          assert.equal(end.passed, false);
          assert.match(end.error, crash);
        } else {
          assert.equal(end.passed, true, end.error);
        }
      }
      assert.equal(events.at(-1).event, "done");
    });

    test("an error the program reports fails that test and the rest carry on", async () => {
      const shown = twoSum.tests.filter((t) => t.visibility === "shown");
      const { ends } = await tc.tests(twoSum, solutions.twoSumThrows, shown);
      assert.equal(ends[0].passed, false);
      assert.match(ends[0].error, thrown);
      assert.deepEqual(failures(ends.slice(1)), []);
    });

    test("a compile error names the file and line", async () => {
      const { build } = await tc.tests(twoSum, solutions.syntaxError, twoSum.tests);
      assert.equal(build.ok, false);
      const errors = build.diagnostics.filter((d) => d.severity === "error");
      assert.ok(errors.length);
      assert.equal(errors[0].file, twoSum.langs[language].file);
      assert.equal(errors[0].line, 3);
    });

    test("a changed signature fails in the tests' code, which the message says", async () => {
      const { compileErrorText } = await importSite("compiled.js");
      const { build } = await tc.tests(twoSum, solutions.renamed, twoSum.tests);
      assert.equal(build.ok, false);
      const harness = language === "java" ? "SweMain.java" : "main.cpp";
      assert.ok(build.diagnostics.some((d) => d.severity === "error" && d.file === harness), JSON.stringify(build.diagnostics));
      const text = compileErrorText(build.diagnostics, { file: twoSum.langs[language].file, harness });
      assert.match(text, /Keep those signatures/);
    });

    test("at the page's limits for this language, a quadratic solution is too slow", async () => {
      const { scaleLimits } = await importSite("compiled.js");
      const tests = scaleLimits(twoSum.tests, language);
      const fast = await tc.tests(twoSum, solutions.twoSum, tests);
      assert.deepEqual(failures(fast.ends), []);
      const slow = await tc.tests(twoSum, solutions.twoSumNaive, tests);
      const timed = slow.ends.filter((e) => tests.find((t) => t.id === e.id).limit_ms);
      assert.ok(timed.some((e) => /^Too slow: this test took/.test(e.error ?? "")), JSON.stringify(timed.map((e) => e.error)));
      assert.deepEqual(failures(slow.ends.filter((e) => !timed.includes(e))), []);
    });

    test("scratch runs main with the solution", async () => {
      const item = data.algo.problems.find((p) => p.problem.id === TWO_SUM);
      const { build, out, exitCode } = await tc.scratch(twoSum, solutions.twoSum, item.langs[language].scratch_starter);
      assert.ok(build.ok, JSON.stringify(build.diagnostics));
      assert.equal(exitCode, 0);
      assert.equal(out, "n=4\n[0, 1]\n");
    });
  });

  // Every problem's starter code builds with its tests at every level, without a warning, and
  // runs every test to the end; every scratch starter builds and runs.
  describe(`${language}: every starter builds and runs`, () => {
    for (const item of data.problems) {
      const id = item.problem.id;
      for (const level of data.levels) {
        test(`${id} level ${level}`, async () => {
          const file = await readSiteJson(`tests/coding/${id}.json`);
          const lang = item.langs[language];
          const code = withStubs(lang.starter_code, lang.stubs, level);
          const tests = file.tests.filter((t) => t.level <= level);
          const { build, ends, messages } = await tc.tests(file, code, tests, level);
          assert.ok(build.ok, JSON.stringify(build.diagnostics));
          assert.deepEqual(build.diagnostics.filter((d) => d.file === lang.file), []);
          assert.deepEqual(messages.filter((m) => m.type === "fatal"), []);
          assert.equal(ends.length, tests.length);
          if (starterError) assert.match(ends[0].error ?? "", starterError);
        });
      }
      test(`${id} scratch`, async () => {
        const file = await readSiteJson(`tests/coding/${id}.json`);
        const { build, messages, exitCode } = await tc.scratch(file, item.langs[language].starter_code, item.langs[language].scratch_starter);
        assert.ok(build.ok, JSON.stringify(build.diagnostics));
        assert.deepEqual(messages.filter((m) => m.type === "fatal"), []);
        assert.equal(typeof exitCode, "number");
      });
    }
    for (const item of data.algo.problems) {
      const id = item.problem.id;
      test(id, async () => {
        const file = await readSiteJson(`tests/algo/${id}.json`);
        const lang = item.langs[language];
        const { build, ends, messages } = await tc.tests(file, lang.starter_code, file.tests);
        assert.ok(build.ok, JSON.stringify(build.diagnostics));
        assert.deepEqual(build.diagnostics.filter((d) => d.file === lang.file), []);
        assert.deepEqual(messages.filter((m) => m.type === "fatal"), []);
        // The first too-slow test stops a submit; the starter fails fast, so all of them end.
        assert.equal(ends.length, file.tests.length);
        const scratch = await tc.scratch(file, lang.starter_code, lang.scratch_starter);
        assert.ok(scratch.build.ok, JSON.stringify(scratch.build.diagnostics));
        assert.deepEqual(scratch.messages.filter((m) => m.type === "fatal"), []);
      });
    }
  });
}
