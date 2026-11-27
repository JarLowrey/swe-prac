// lint.js (ruff compiled to WebAssembly, with data.json's settings) finds what native ruff finds
// with the config files they come from, and formats the same. Columns differ on purpose: the page
// counts UTF-16 units, as the editor does, and native ruff counts characters.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { before, describe, test } from "node:test";

import { REPO, data, ruff } from "./harness.mjs";

const NATIVE = process.env.RUFF
  ?? [join(REPO, ".venv", "Scripts", "ruff.exe"), join(REPO, ".venv", "bin", "ruff")].find(existsSync)
  ?? "ruff";
const CONFIGS = {
  coding: join(REPO, "swe_prac", "user_ruff.toml"),
  algo: join(REPO, "swe_prac", "user_ruff_algo.toml"),
};

function native(args, code) {
  const out = spawnSync(NATIVE, [...args, "--stdin-filename", "solution.py", "-"], {
    input: code, encoding: "utf8", cwd: REPO,
  });
  if (out.error) throw new Error(`Can't run ruff (${NATIVE}): ${out.error.message}. Set RUFF to its path.`);
  return out;
}

// A 1-based column in characters as one in UTF-16 units.
const utf16Column = (line, col) => [...line].slice(0, col - 1).join("").length + 1;

function nativeLint(code, track) {
  const out = native(["check", "--no-cache", "--output-format", "json", "--config", CONFIGS[track]], code);
  const lines = code.split("\n");
  const issues = JSON.parse(out.stdout).map((d) => ({
    code: d.code ?? "syntax",
    message: d.message,
    row: d.location.row,
    col: utf16Column(lines[d.location.row - 1] ?? "", d.location.column),
    end_row: d.end_location.row,
    end_col: utf16Column(lines[d.end_location.row - 1] ?? "", d.end_location.column),
    fixable: d.fix != null,
  }));
  return issues.sort((a, b) => a.row - b.row || a.col - b.col);
}

function nativeFormat(code, track) {
  const out = native(["format", "--no-cache", "--config", CONFIGS[track]], code);
  return out.status === 0 ? out.stdout : null;
}

const MESSY = {
  "unused imports, camelCase and a long line": `import os, sys
from typing import List
def twoSum(nums: List[int], targetValue) -> List[int]:
    seen = {}
    for i in range(len(nums)):
        if targetValue-nums[i] in seen: return [seen[targetValue-nums[i]], i]
        seen[nums[i]] = i
    x = "${"a".repeat(120)}"
    return None
`,
  "non-ASCII text before the problems": `class Solution:
    def greet(self) -> str:
        note = "naïve café ✓"; unused = 1
        emoji = "🙂🙂"; l = [x for x in [1,2] ]
        return note + emoji
`,
  "a syntax error": `class Solution:
    def f(self, n)
        return n
`,
  "tabs and trailing whitespace": "def f(a):\n\tif a == None:  \n\t\treturn True\n\treturn a\n",
  "a mutable default and a bare except": `def f(x=[]):
    try:
        return x[0]
    except:
        pass
`,
};

const CASES = [
  ...Object.entries(MESSY).map(([name, code]) => ({ name, code })),
  ...data.problems.flatMap((p) => [
    { name: `${p.problem.id} reference`, code: p.reference_code, tracks: ["coding"] },
    { name: `${p.problem.id} starter`, code: p.starter_code, tracks: ["coding"] },
  ]),
  ...data.algo.problems.map((p) => ({
    name: `${p.problem.id} reference`,
    code: readFileSync(join(REPO, "algorithms", p.problem.id, "solution.py"), "utf8"),
    tracks: ["algo"],
  })),
];

let lint;
before(async () => {
  lint = await ruff();
});

describe("lint matches native ruff", () => {
  for (const { name, code, tracks = ["coding", "algo"] } of CASES) {
    for (const track of tracks) {
      test(`${name} (${track})`, async () => {
        const got = await lint.lint(code, data.ruff[track]);
        assert.equal(got.error, null);
        assert.deepEqual(got.issues, nativeLint(code, track));
      });
    }
  }

  test("the messy cases do find problems, of the kinds each config checks", async () => {
    const codes = async (track) => new Set((await lint.lint(MESSY["unused imports, camelCase and a long line"], data.ruff[track])).issues.map((i) => i.code));
    const coding = await codes("coding");
    const algo = await codes("algo");
    for (const code of ["F401", "E501", "N802", "N803", "UP006"]) assert.ok(coding.has(code), code);
    assert.ok(!algo.has("N802") && !algo.has("N803")); // algorithms keep the conventional camelCase
    const syntax = await lint.lint(MESSY["a syntax error"], data.ruff.coding);
    assert.equal(syntax.issues[0].code, "invalid-syntax"); // common.js shows it as an error
  });
});

describe("format matches native ruff", () => {
  for (const [name, code] of Object.entries(MESSY)) {
    test(name, async () => {
      const got = await lint.format(code, data.ruff.coding);
      const expected = nativeFormat(code, "coding");
      if (expected === null) {
        assert.equal(got.code, null);
        assert.ok(got.error);
      } else {
        assert.deepEqual(got, { code: expected, error: null });
      }
    });
  }
});
