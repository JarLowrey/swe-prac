// Java: the compiler and runner on the built site's javac and TeaVM (see compiled-suite.mjs),
// and compiled.js, the page's side of it.
import assert from "node:assert/strict";
import { after, before, describe, test } from "node:test";

import { compiledSuite } from "./compiled-suite.mjs";
import { data, importSite, readSiteJson } from "./harness.mjs";

const TWO_SUM_ID = data.algo.problems.find((p) => p.problem.id.endsWith("two_sum")).problem.id;

const TWO_SUM = `import java.util.*;

class Solution {
    public int[] twoSum(int[] nums, int target) {
        BODY
        Map<Integer, Integer> seen = new HashMap<>();
        for (int i = 0; i < nums.length; i++) {
            Integer j = seen.get(target - nums[i]);
            if (j != null) return new int[] {j, i};
            seen.put(nums[i], i);
        }
        return new int[0];
    }
}
`;

const twoSum = (body) => TWO_SUM.replace("BODY", body);

compiledSuite("java", {
  solutions: {
    twoSum: twoSum('System.out.println("n=" + nums.length);'),
    twoSumNaive: twoSum("for (int i = 0; i < nums.length; i++) for (int j = i + 1; j < nums.length; j++) if (nums[i] + nums[j] == target) return new int[] {i, j};"),
    // A null dereference stops a TeaVM program: it can't be caught.
    twoSumBroken: twoSum("if (nums.length == 4) { String none = null; return new int[] {none.length()}; }"),
    twoSumThrows: twoSum('if (nums.length == 4) throw new IllegalArgumentException("four");'),
    fileStore: `import java.util.*;

class FileStore {
    private final Map<String, Integer> files = new HashMap<>();

    public boolean addFile(int timestamp, String name, int size) {
        return files.putIfAbsent(name, size) == null;
    }

    public Integer getFileSize(int timestamp, String name) {
        return files.get(name);
    }

    public Integer deleteFile(int timestamp, String name) {
        return files.remove(name);
    }
}
`,
    syntaxError: "import java.util.*;\n\nclass Solution { public int[] twoSum(int[] nums, int target) { return nums } }\n",
    renamed: twoSum("").replace("twoSum(", "twoSums("),
  },
  crash: /NullPointerException/,
  thrown: /IllegalArgumentException/,
  starterError: /UnsupportedOperationException/,
});

// compiled.js end to end: the compile worker (lang-compile.js) and a fresh run worker per job
// (lang-run.js) on harness.mjs's Worker stand-in, with the page's time limits.
describe("java: compiled.js", () => {
  let java;
  let file;
  before(async () => {
    ({ java } = await importSite("compiled.js"));
    file = await readSiteJson(`tests/algo/${TWO_SUM_ID}.json`);
  });
  after(() => java.coolDown());

  const lang = () => file.langs.java;
  const shown = () => file.tests.filter((t) => t.visibility === "shown");

  test("Submit reports each test, and the build's warnings as the lint", async () => {
    const run = await java.runTests({ code: twoSum(""), tests: file.tests, options: file.options, lang: lang() });
    assert.equal(run.import_error, null);
    assert.equal(run.compile_error, false);
    assert.deepEqual(Object.values(run.results).filter((r) => !r.passed), []);
    assert.equal(Object.keys(run.results).length, file.tests.length);
    assert.deepEqual(run.lint, { issues: [], error: null });
  });

  test("a compile error is the run's load error, and lint marks its line", async () => {
    const code = "import java.util.*;\n\nclass Solution { public int[] twoSum(int[] nums, int target) { return nums } }\n";
    const run = await java.runTests({ code, tests: shown(), options: file.options, lang: lang() });
    assert.equal(run.compile_error, true);
    assert.match(run.import_error, /Solution\.java:3:\d+: error: /);
    const lint = await java.lint({ code, lang: lang() });
    assert.deepEqual(lint.issues.map((i) => [i.code, i.row]), [["error", 3]]);
  });

  test("a call that runs far past its limit is stopped as too slow", async () => {
    const code = twoSum("while (nums.length > 0) { }");
    const test1 = { ...shown()[0], limit_ms: 100 };
    const started = performance.now();
    const run = await java.runTests({ code, tests: [test1], options: file.options, lang: lang() });
    assert.match(run.results[test1.id].error, /^Too slow: stopped after/);
    assert.ok(performance.now() - started < 8000);
    // The next run gets a fresh worker.
    const again = await java.runTests({ code: twoSum(""), tests: shown(), options: file.options, lang: lang() });
    assert.deepEqual(Object.values(again.results).filter((r) => !r.passed), []);
  });

  test("Run scratch prints what main prints", async () => {
    const item = data.algo.problems.find((p) => p.problem.id === TWO_SUM_ID);
    const out = await java.runScratch({ code: twoSum(""), scratch: item.langs.java.scratch_starter, lang: lang() });
    assert.equal(out.stdout, "[0, 1]\n");
    assert.equal(out.exit_code, 0);
    const thrown = await java.runScratch({ code: twoSum('if (true) throw new IllegalStateException("no");'), scratch: item.langs.java.scratch_starter, lang: lang() });
    assert.equal(thrown.exit_code, 1);
    assert.match(thrown.stderr, /Exception in thread "main" java\.lang\.IllegalStateException: no/);
  });
});
