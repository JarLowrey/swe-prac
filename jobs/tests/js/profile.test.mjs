// The Skills page's profile form: the reference/profile.yaml it writes, and the zip it goes into.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { test } from "node:test";
import { SITE, importSite } from "./harness.mjs";

const { FIELDS, missing, parseDocs, profileYaml } = await importSite("jobs/profile.js");
const { addFile, crc32 } = await importSite("jobs/zip.js");

const FILLED = {
  "identity.first_name": " Ada ", "identity.last_name": "Example", "identity.pronouns": "she/her",
  "identity.email": "ada@example.com", "identity.phone": "303-555-0100",
  "identity.linkedin_url": "www.linkedin.com/in/ada-example", "identity.github_url": "",
  "location.city": "Denver", "location.state": "CO", "location.country": "United States",
  "location.acceptable_locations": "Denver area, hybrid\n\n  Remote within the US ",
  "location.open_to_relocation": true,
  "work_authorization.citizenship": "us_citizen", "work_authorization.authorized_to_work_in_us": "true",
  "work_authorization.requires_sponsorship_now": "false", "work_authorization.requires_sponsorship_future": "false",
  "work_authorization.willing_to_obtain_clearance": "true",
  "military.military_spouse": "false", "consents.ai_application_review": "true",
  "eeo.veteran_status": "not_a_protected_veteran", "eeo.race": "not-an-option",
  "preferences.target_roles": "Senior backend engineer", "preferences.salary_expectation": "$180,000",
  "resume.file": "C:\\Users\\ada\\Ada \"A\" Example.pdf",
  reference_docs: "https://docs.google.com/document/d/abc/edit - On-call redesign\nnot a link\ndocs.google.com/document/d/xyz",
  "contacts.shared_background": "Denver Go meetup",
};

test("a blank profile marks what the skills need as TODO and declines every self-ID question", () => {
  const y = profileYaml({});
  for (const line of ['  first_name: "TODO"', '  email: "TODO"', '  acceptable_locations:\n    - "TODO"',
    "  citizenship: TODO", "  authorized_to_work_in_us: TODO", "  willing_to_obtain_clearance: TODO",
    '  target_roles: "TODO"', '  path: "TODO"', '  preferred_name: ""', '  pronouns: ""',
    "  security_clearance: none", '  salary_expectation: "ask-per-job"', "  open_to_relocation: false",
    "reference_docs: []", "  shared_background: []", 'reference_folder: "reference"']) {
    assert.ok(y.includes(line), line);
  }
  for (const k of ["gender", "pronouns", "hispanic_or_latino", "race", "veteran_status", "disability_status",
    "sexual_orientation", "transgender", "lgbtqia", "other_self_id_questions"]) {
    assert.ok(y.includes(`\n  ${k}: decline\n`), k);
  }
  assert.doesNotMatch(y, /^(military|consents):/m, "unanswered yes/no screening questions are left out, so the skills ask");
  assert.deepEqual(missing({}), FIELDS.filter((f) => f.required).map((f) => f.label));
});

test("a filled profile writes what was typed, cleaned up", () => {
  const y = profileYaml(FILLED);
  for (const line of ['  first_name: "Ada"', "  pronouns: she/her\n  email:", '  linkedin_url: "https://www.linkedin.com/in/ada-example"',
    '  github_url: ""', "  open_to_relocation: true",
    '  acceptable_locations:\n    - "Denver area, hybrid"\n    - "Remote within the US"\n',
    "  citizenship: us_citizen", "  authorized_to_work_in_us: true", "  requires_sponsorship_now: false",
    "military:\n  military_spouse: false\n\n", "consents:\n  ai_application_review: true\n\n",
    "  veteran_status: not_a_protected_veteran", "  race: decline", '  salary_expectation: "$180,000"',
    '  path: "reference/Ada \\"A\\" Example.pdf"',
    'reference_docs:\n  - url: "https://docs.google.com/document/d/abc/edit"\n    use_for: "On-call redesign"\n'
      + '  - url: "https://docs.google.com/document/d/xyz"\n    use_for: "Reference material"\n',
    '  shared_background:\n    - "Denver Go meetup"']) {
    assert.ok(y.includes(line), line);
  }
  assert.match(y, /^eeo:\n {2}gender: decline\n {2}pronouns: she\/her\n/m, "self-ID pronouns follow the ones you gave");
  assert.deepEqual(missing(FILLED), []);
});

test("every line is a comment, a key, or a list item, two spaces deep at most", () => {
  for (const line of profileYaml(FILLED).split("\n")) {
    assert.match(line, /^(|#.*|[a-z_]+:( .+)?| {2}[a-z_]+:( .+)?| {2}- url: ".+"| {4}use_for: ".+"| {4}- ".*")$/, line);
  }
});

test("Drive doc lines: a link, then what it covers", () => {
  assert.deepEqual(parseDocs("https://d.example/1   Design doc: the ledger\nhttps://d.example/2: Stories\n\nnotes"),
    [{ url: "https://d.example/1", useFor: "Design doc: the ledger" }, { url: "https://d.example/2", useFor: "Stories" }]);
});

test("the kit download gets the profile added, and stays a valid zip", async () => {
  assert.equal(crc32(new TextEncoder().encode("123456789")), 0xcbf43926);
  const kit = new Uint8Array(await readFile(join(SITE, "jobs", "job-search.zip")));
  const text = profileYaml(FILLED);
  const out = addFile(kit, "job-search/reference/profile.yaml", text, new Date(2026, 10, 26, 9, 30));
  const { loadPyodide } = await importSite("practice/vendor/pyodide/pyodide.mjs");
  const pyodide = await loadPyodide();
  pyodide.globals.set("before", kit);
  pyodide.globals.set("after", out);
  const result = JSON.parse(pyodide.runPython(`
import io, json, zipfile
old = zipfile.ZipFile(io.BytesIO(bytes(before.to_py())))
new = zipfile.ZipFile(io.BytesIO(bytes(after.to_py())))
info = new.getinfo("job-search/reference/profile.yaml")
json.dumps({
  "bad": new.testzip(),
  "names": new.namelist(),
  "old": old.namelist(),
  "same": all(old.read(n) == new.read(n) for n in old.namelist()),
  "text": new.read(info).decode("utf-8"),
  "when": list(info.date_time),
  "mode": oct(info.external_attr >> 16),
})`));
  assert.equal(result.bad, null, "every entry's CRC checks out");
  assert.deepEqual(result.names, [...result.old, "job-search/reference/profile.yaml"]);
  assert.ok(result.same, "the kit's files are unchanged");
  assert.equal(result.text, text);
  assert.deepEqual(result.when, [2026, 11, 26, 9, 30, 0]);
  assert.equal(result.mode, "0o100644");
  assert.throws(() => addFile(new Uint8Array(40), "x", "y"), /isn't a zip/);
});
