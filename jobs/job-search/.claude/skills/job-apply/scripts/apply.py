#!/usr/bin/env python3
"""Pipeline driver for the job-apply skill.

Doing several applications in one conversation lets steps slip: the model
fills the forms and forgets the LinkedIn contacts. This script takes that
decision away. It runs each step of each application as its own short
`claude -p` agent, then checks the files the step must leave behind. A step
that left nothing is retried, then reported as FAILED. Tracker rows are written
by the script itself, never left to an agent.

Steps, in order (every one has a check):
  read      posting read, location checked      -> job.md           (agent)
  fill      form filled, answers drafted        -> fill-log.md      (agent)
            (and answers.md when there are written questions)
  contacts  people to reach out to              -> contacts.md      (agent)
  log       tracker row with folder and status  -> tracker.csv      (script)

fill and contacts don't depend on each other, so a form blocked on a sign-in
page does not stop the contacts step. Agents run one at a time: they share one
Chrome, and LinkedIn limits accounts that browse fast (see --linkedin-delay).

Usage:
  apply.py run URL [URL ...]      all steps for each link; safe to re-run, steps
                                  whose files already pass their check are skipped
  apply.py audit                  list every application folder and the steps
                                  it is missing (exit code 1 if any)
  apply.py backfill               run the missing steps for existing
                                  applications (default: contacts and log)

Nothing here submits an application or contacts anyone; the agents are told
the same rules as the skills.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tracker  # noqa: E402

SKILLS_DIR = HERE.parents[1]
PHASES = ("read", "fill", "contacts", "log")
# Statuses after the form has gone in: never re-run fill for these.
SENT = ("submitted", "interviewing", "rejected", "offer", "withdrawn")
CONTACTS_MAX_AGE_DAYS = 30


def say(msg: str = "") -> None:
    print(msg, flush=True)


def root() -> Path:
    return tracker.data_dir()


# --------------------------------------------------------------------------
# One application
# --------------------------------------------------------------------------

@dataclass
class App:
    url: str = ""
    company: str = ""
    role: str = ""
    location: str = ""
    ats: str = ""
    status: str = ""
    row_id: str = ""  # tracker row this application was matched to
    folder: Path | None = None
    written_questions: int | None = None
    tracker_note: str = ""
    needs_you: list[str] = field(default_factory=list)
    results: dict = field(default_factory=dict)  # phase -> short outcome text
    failed: list[str] = field(default_factory=list)
    cost: float = 0.0
    skipped: bool = False

    @property
    def label(self) -> str:
        if self.company or self.role:
            return f"{self.company}: {self.role}".strip(": ")
        return self.folder.name if self.folder else self.url

    def file(self, name: str) -> Path | None:
        return self.folder / name if self.folder else None


def norm_path(p) -> str:
    return os.path.normcase(os.path.normpath(str(p))) if p else ""


def read_text(path: Path | None) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path and path.exists() else ""


def parse_job_md(text: str) -> dict:
    def field_(label: str) -> str:
        m = re.search(rf"\*\*{label}[^*\n]*:\*\*\s*(.+)", text, re.I)
        return m.group(1).strip().strip("<>") if m else ""
    return {"company": field_("Company"), "role": field_("Title"),
            "location": field_("Location"), "url": field_("URL")}


def app_from_folder(folder: Path, rows: list[dict]) -> App:
    info = parse_job_md(read_text(folder / "job.md"))
    row = next((r for r in rows if norm_path(r["folder"]) == norm_path(folder)), None)
    if row is None and info["url"]:
        row = next(iter(tracker.find_rows(rows, url=info["url"])), None)
    app = App(folder=folder, url=info["url"], company=info["company"],
              role=info["role"], location=info["location"])
    if row:  # the tracker's short names beat the job.md header, which can run long
        app.row_id = row["id"]
        app.url = row["url"] or app.url
        app.company = row["company"] or app.company
        app.role = row["role"] or app.role
        app.location = row["location"] or app.location
        app.ats, app.status = row["ats"], row["status"]
    return app


def tracker_row(app: App, rows: list[dict] | None = None) -> dict | None:
    rows = tracker.load() if rows is None else rows
    if app.folder:
        for r in rows:
            if norm_path(r["folder"]) == norm_path(app.folder):
                return r
    return next(iter(tracker.find_rows(rows, url=app.url)), None) if app.url else None


# --------------------------------------------------------------------------
# Checks. Each returns a list of problems; an empty list means the step is done.
# --------------------------------------------------------------------------

def gate_read(app: App) -> list[str]:
    if not app.folder or not app.folder.is_dir():
        return ["application folder is missing"]
    if len(read_text(app.file("job.md"))) < 500:
        return ["job.md is missing or shorter than 500 characters"]
    return []


def gate_fill(app: App) -> list[str]:
    if not app.folder:
        return ["no application folder"]
    log = read_text(app.file("fill-log.md"))
    problems = []
    if len(log) < 150:
        problems.append("fill-log.md is missing or too short")
    if ((app.written_questions or 0) > 0 or "answers.md" in log) and not app.file("answers.md").exists():
        problems.append("answers.md is missing, but the form has written questions")
    return problems


def gate_contacts(app: App) -> list[str]:
    if not app.folder:
        return ["no application folder"]
    text = read_text(app.file("contacts.md"))
    if not text:
        return ["contacts.md is missing"]
    if "# Contacts" not in text:
        return ["contacts.md has no '# Contacts' heading (wrong format)"]
    none_found = re.search(r"no (suitable|good|qualified|usable) (contacts|matches|people)|none found", text, re.I)
    if "Connection note" not in text and not none_found:
        return ["contacts.md lists nobody and doesn't say why"]
    return []


def gate_log(app: App) -> list[str]:
    row = tracker_row(app)
    if row is None:
        return ["no tracker row"]
    if not row["folder"] or not row["status"]:
        return ["tracker row has no folder or status"]
    return []


GATES = {"read": gate_read, "fill": gate_fill, "contacts": gate_contacts, "log": gate_log}


def needed_phases(app: App, phases=PHASES, refill: bool = False) -> dict[str, list[str]]:
    """Steps whose check fails for this application, with the problems."""
    if app.status.startswith("skipped"):
        wanted = ("read", "log") if app.folder else ("log",)
    else:
        wanted = phases
    out = {}
    for phase in PHASES:
        if phase not in wanted or phase not in phases:
            continue
        if phase == "fill" and app.status in SENT and not refill:
            continue
        problems = GATES[phase](app)
        if problems:
            out[phase] = problems
    return out


# --------------------------------------------------------------------------
# Tracker (written by the script, not by an agent)
# --------------------------------------------------------------------------

def sync_tracker(app: App, note: str = "") -> None:
    if not app.url:
        return
    rows = tracker.load()
    hit = tracker_row(app, rows)  # must be a row of this same list, which is what gets saved
    status = app.status or "in-progress"
    if hit:
        for key, value in (("status", status), ("folder", str(app.folder or "")),
                           ("location", app.location), ("ats", app.ats),
                           ("company", app.company), ("role", app.role)):
            if value and (key in ("status", "folder") or not hit[key]):
                hit[key] = value
        if note:
            hit["notes"] = tracker.append_note(hit["notes"], note)
        hit["date_updated"] = tracker.today()
    else:
        next_id = max((int(r["id"]) for r in rows if r["id"].isdigit()), default=0) + 1
        rows.append({
            "id": str(next_id), "date_added": tracker.today(), "company": app.company,
            "role": app.role, "location": app.location, "url": app.url, "ats": app.ats,
            "status": status, "date_updated": tracker.today(),
            "folder": str(app.folder or ""),
            "notes": tracker.append_note("", note) if note else "",
        })
    tracker.save(rows)
    app.status = status


# --------------------------------------------------------------------------
# Agent prompts and result schemas
# --------------------------------------------------------------------------

COMMON = """\
You are one step of a scripted job-application pipeline. A Python driver runs the steps in order and checks the files you leave behind when you finish, so do this step completely and nothing else.

Rules (the same as the job-apply skill's):
- Never click the final Submit / Send application button, and never tick terms, privacy-policy or attestation boxes.
- Never send LinkedIn connection requests or messages.
- When the profile or resume doesn't answer a form question, leave it blank and list it; don't guess.
- Don't edit tracker.csv. The driver logs the application.
- Nobody can answer questions. If you are blocked (sign-in page, CAPTCHA, a permission you don't have), stop this step, write down what you finished and why you stopped, and return that in your final answer.
- The job-search folder is {root}. Application folders are {root}/applications/<YYYY-MM-DD>-<company>-<role>/ (lowercase, hyphens, under about 60 characters).
- Skill files: {skills}/<skill-name>/SKILL.md. Load the skill with the Skill tool, or read that file if the tool can't find it.
"""

PROMPTS = {
    "read": """\
STEP: READ THE POSTING (job-apply skill, step 1 only; do not open the application form).
Job link: {url}
1. Open the link in Claude in Chrome and read it with get_page_text. Pull out company, job title, team, location(s), workplace type, pay range and the full description.
2. Compare the location with location.acceptable_locations in reference/profile.yaml. If none match, set outcome to "skipped-location" (you must still do step 3). If it is unclear, continue and say so in notes.
3. Create the application folder and write job.md in it: a header (company, title, location, workplace type, pay range, URL, date read) followed by the posting text copied word for word. Do not paraphrase; postings vanish when roles close.
Return the outcome ("continue" or "skipped-location"), company, role, location, the absolute path of the folder, and notes on anything the user should know (role below their target level, unclear location, poor fit against the resume).
""",
    "fill": """\
STEP: FILL THE FORM (job-apply skill, steps 2 to 5; skip steps 1, 6 and 7).
Job link: {url}
Application folder: {folder} (job.md there holds the posting; don't rewrite it).
Open the application in Chrome and fill it from the profile and resume as the skill describes. Use the job-answers skill for written questions; it writes answers.md in the folder. Paste the drafts into the fields, except anti-AI "human-check" questions, which the skill says to leave for the user. Stop before Submit. Write fill-log.md in the folder as the skill describes, and leave the tab open on the form.
Return status "ready-for-review" if the form is filled and only the user's own items remain, or "in-progress" if you couldn't finish (sign-in needed, errors, blocked). Also return the ATS name, how many free-text written questions the form has (human-check ones included), the list of things the user must do or decide, and a one-line note for the tracker (pay range, fit gaps, what's still needed).
""",
    "contacts": """\
STEP: FIND PEOPLE TO CONTACT (the job-contacts skill).
Company: {company}
Role: {role}
Location: {location}
Application folder: {folder} (job.md there holds the posting).
Find the people the skill describes and write contacts.md in that folder, in the skill's format, with a connection note and a follow-up message for each person. Nothing is sent. If you find fewer people than the skill's target, say why in contacts.md.
{sibling}Return how many people you found and a one-line summary.
""",
}

SIBLING = ("An earlier application at this company already has {path} (found {when}). "
           "Start from it as the skill says and re-tailor the notes for this role.\n")

SCHEMAS = {
    "read": {"type": "object", "required": ["outcome", "company", "role", "location", "folder"],
             "properties": {"outcome": {"enum": ["continue", "skipped-location", "blocked"]},
                            "company": {"type": "string"}, "role": {"type": "string"},
                            "location": {"type": "string"}, "folder": {"type": "string"},
                            "notes": {"type": "string"}, "blocked_reason": {"type": "string"}}},
    "fill": {"type": "object", "required": ["status", "ats", "written_questions", "needs_you", "tracker_note"],
             "properties": {"status": {"enum": ["ready-for-review", "in-progress"]},
                            "ats": {"type": "string"}, "written_questions": {"type": "integer"},
                            "needs_you": {"type": "array", "items": {"type": "string"}},
                            "tracker_note": {"type": "string"}, "blocked_reason": {"type": "string"}}},
    "contacts": {"type": "object", "required": ["people", "summary"],
                 "properties": {"people": {"type": "integer"}, "summary": {"type": "string"},
                                "blocked_reason": {"type": "string"}}},
}


def apply_result(app: App, phase: str, out: dict) -> None:
    """Copy an agent's structured answer onto the App. Raises ValueError if it can't be used."""
    if phase == "read":
        if out.get("outcome") == "blocked":
            raise ValueError("blocked: " + (out.get("blocked_reason") or out.get("notes") or "no reason given"))
        folder = Path(out["folder"]).expanduser()
        apps_dir = (root() / "applications").resolve()
        if not folder.resolve().is_relative_to(apps_dir):
            raise ValueError(f"folder {folder} is not inside {apps_dir}")
        app.folder = folder
        app.company, app.role, app.location = out["company"], out["role"], out["location"]
        app.skipped = out["outcome"] == "skipped-location"
        if app.skipped:
            app.status = "skipped-location"
        if out.get("notes"):
            app.needs_you.append(out["notes"])
    elif phase == "fill":
        app.status = out.get("status") or "in-progress"
        app.ats = out.get("ats") or app.ats
        app.written_questions = out.get("written_questions")
        app.tracker_note = out.get("tracker_note", "")
        app.needs_you.extend(out.get("needs_you") or [])
        if out.get("blocked_reason"):
            app.needs_you.append("blocked: " + out["blocked_reason"])
    elif phase == "contacts":
        app.results["contacts"] = f"{out.get('people', '?')} people. {out.get('summary', '')}".strip()


# --------------------------------------------------------------------------
# Running an agent
# --------------------------------------------------------------------------

_last_linkedin = 0.0


def agent_command(args) -> list[str]:
    override = os.environ.get("JOB_APPLY_AGENT_CMD")  # JSON list; lets tests stub the agent
    if override:
        return json.loads(override)
    exe = shutil.which("claude")
    if not exe:
        sys.exit("The `claude` command isn't on PATH. Install Claude Code first.")
    return [exe]


def run_agent(app: App, phase: str, prompt: str, args) -> tuple[dict | None, str]:
    """One `claude -p` call. Returns (structured answer or None, error text)."""
    cmd = agent_command(args) + [
        "-p", "--output-format", "json", "--json-schema", json.dumps(SCHEMAS[phase]),
        "--permission-mode", args.permission_mode, "--permission-prompts", "none",
        "--max-budget-usd", str(args.budget), "-n", f"job-apply {phase}: {app.label}"[:80],
    ]
    if not args.no_chrome:
        cmd.append("--chrome")
    if args.model:
        cmd += ["--model", args.model]
    if args.effort:
        cmd += ["--effort", args.effort]
    env = {**os.environ, "JOB_SEARCH_DIR": str(root()), "PIPELINE_PHASE": phase}
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", cwd=root(), env=env, timeout=args.timeout * 60)
    except subprocess.TimeoutExpired:
        return None, f"timed out after {args.timeout} minutes"
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        tail = (proc.stderr or proc.stdout or "").strip()[-300:]
        return None, f"claude exited {proc.returncode} without a JSON result: {tail}"
    app.cost += float(data.get("total_cost_usd") or 0)
    error = ""
    if data.get("is_error"):
        error = str(data.get("result") or data.get("subtype") or "agent reported an error")[:300]
    denials = data.get("permission_denials") or []
    if denials:
        error = (error + " " if error else "") + "permission denied: " + json.dumps(denials)[:300]
    out = data.get("structured_output")
    if out is None and isinstance(data.get("result"), str):
        try:
            out = json.loads(data["result"])
        except json.JSONDecodeError:
            pass
    return out, error


def run_phase(app: App, phase: str, args) -> bool:
    """Run one agent step until its check passes or the attempts run out."""
    global _last_linkedin
    feedback = ""
    for attempt in range(1, args.retries + 2):
        if phase == "contacts":
            wait = _last_linkedin + args.linkedin_delay - time.monotonic()
            if _last_linkedin and wait > 0:
                say(f"    waiting {wait:.0f}s between LinkedIn searches")
                time.sleep(wait)
        prompt = COMMON.format(root=root(), skills=SKILLS_DIR) + "\n" + PROMPTS[phase].format(
            url=app.url, folder=app.folder, company=app.company or "(see job.md)",
            role=app.role or "(see job.md)", location=app.location or "(see job.md)",
            sibling=sibling_note(app) if phase == "contacts" else "")
        if feedback:
            prompt += f"\nA previous attempt at this step failed these checks. Fix them:\n{feedback}\n"
        say(f"  {phase}: running agent (attempt {attempt} of {args.retries + 1})...")
        start = time.monotonic()
        out, error = run_agent(app, phase, prompt, args)
        if phase == "contacts":
            _last_linkedin = time.monotonic()
        problems = [error] if error else []
        if out is None:
            problems.append("agent returned no structured answer")
        else:
            try:
                apply_result(app, phase, out)
            except ValueError as exc:
                problems.append(str(exc))
            except KeyError as exc:
                problems.append(f"agent's answer is missing the field {exc}")
        say(f"    done in {time.monotonic() - start:.0f}s, ${app.cost:.2f} so far")
        failed_checks = GATES[phase](app)
        if not failed_checks:  # the files are what count, not what the agent says
            if problems:
                app.needs_you.append(f"{phase} agent warning: {'; '.join(problems)}")
            return True
        problems = list(dict.fromkeys(problems + failed_checks))
        feedback = "\n".join(f"- {p}" for p in problems)
        say("    check failed: " + "; ".join(problems))
    return False


def sibling_note(app: App) -> str:
    """Point the agent at an earlier contacts.md for the same company."""
    name = app.company.strip().lower()
    if not name:
        return ""
    for row in tracker.load():
        if row["company"].strip().lower() != name or not row["folder"]:
            continue
        folder = Path(row["folder"])
        if norm_path(folder) == norm_path(app.folder):
            continue
        candidate = folder / "contacts.md"
        age_days = (time.time() - candidate.stat().st_mtime) / 86400 if candidate.exists() else None
        if age_days is not None and age_days <= CONTACTS_MAX_AGE_DAYS and \
                not gate_contacts(App(folder=folder)):
            when = dt.date.fromtimestamp(candidate.stat().st_mtime).isoformat()
            return SIBLING.format(path=candidate, when=when)
    return ""


# --------------------------------------------------------------------------
# The pipeline for one application
# --------------------------------------------------------------------------

def process(app: App, phases: tuple[str, ...], args) -> bool:
    """Run the steps in `phases` that still fail their check. True if all checks pass."""
    row = tracker_row(app)
    if row and not app.status:
        app.status = row["status"]
    if app.status.startswith("skipped") and not args.force:
        say(f"  already logged as {app.status}; nothing to do (use --force to re-run)")
        return True
    if args.dry_run:
        todo = needed_phases(app, phases, refill=args.force)
        say("  would run: " + (", ".join(todo) if todo else "nothing, every check passes"))
        for phase, problems in todo.items():
            say(f"    {phase}: {'; '.join(problems)}")
        return not todo

    for phase in ("read", "fill", "contacts"):
        if phase not in phases:
            continue
        if app.skipped and phase != "read":
            continue  # the posting doesn't fit; don't fill it or look for contacts
        if phase == "fill" and app.status in SENT and not args.force:
            continue
        if not GATES[phase](app):
            app.results.setdefault(phase, "already done")
            continue
        if phase != "read" and gate_read(app):
            app.results[phase] = "FAILED: " + gate_read(app)[0] + " (run the read step first)"
            app.failed.append(phase)
            continue
        if run_phase(app, phase, args):
            app.results[phase] = "ok" if phase != "fill" else f"ok ({app.status})"
            if phase == "read":
                sync_tracker(app, note="location doesn't fit" if app.skipped else "")
            elif phase == "fill":
                sync_tracker(app, note=app.tracker_note)
        else:
            app.results[phase] = "FAILED: " + "; ".join(GATES[phase](app))
            app.failed.append(phase)

    if "log" in phases:
        note = f"INCOMPLETE, missing: {', '.join(app.failed)}" if app.failed else ""
        sync_tracker(app, note=note)
        problems = gate_log(app)
        app.results["log"] = "FAILED: " + "; ".join(problems) if problems else "ok"
        if problems:
            app.failed.append("log")
    return not app.failed


def print_app_report(app: App) -> None:
    say(f"\n== {app.label}")
    if app.url:
        say(f"   {app.url}")
    for phase in PHASES:
        if phase in app.results:
            say(f"   {phase:<9} {app.results[phase]}")
    if app.folder:
        say(f"   folder    {app.folder}")
    for item in app.needs_you:
        say(f"   needs you: {item}")


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def parse_phases(text: str | None, default=PHASES) -> tuple[str, ...]:
    if not text:
        return tuple(default)
    wanted = [p.strip() for p in text.split(",") if p.strip()]
    bad = [p for p in wanted if p not in PHASES]
    if bad:
        sys.exit(f"Unknown step(s): {', '.join(bad)}. Steps are: {', '.join(PHASES)}")
    return tuple(p for p in PHASES if p in wanted)


def finish(apps: list[App], args) -> int:
    if args.dry_run:
        say(f"\nDry run: {len(apps)} application(s) would be processed. No agents were started.")
        return 0
    say("\n" + "=" * 60)
    incomplete = [a for a in apps if a.failed]
    total = sum(a.cost for a in apps)
    say(f"{len(apps) - len(incomplete)} of {len(apps)} applications complete. Agent cost ${total:.2f}.")
    for a in incomplete:
        say(f"  INCOMPLETE {a.label}: {', '.join(a.failed)}")
    if incomplete:
        say("Fix the cause (sign-in, a Chrome permission, LinkedIn limit) and re-run the same command. "
            "Steps that already pass their check are skipped.")
    return 1 if incomplete else 0


def cmd_run(args) -> int:
    urls = list(args.urls)
    if args.file:
        urls += [ln.strip() for ln in Path(args.file).read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.lstrip().startswith("#")]
    seen, unique = set(), []
    for url in urls:
        key = tracker.normalize_url(url)
        if key and key not in seen:
            seen.add(key)
            unique.append(url)
    if not unique:
        sys.exit("Give at least one job link, or --file with one link per line.")
    phases = parse_phases(args.only)
    apps = []
    for i, url in enumerate(unique, 1):
        say(f"\n[{i}/{len(unique)}] {url}")
        app = App(url=url)
        row = next(iter(tracker.find_rows(tracker.load(), url=url)), None)
        if row and row["folder"] and Path(row["folder"]).is_dir():
            app = app_from_folder(Path(row["folder"]), tracker.load())
            app.url = app.url or url
            say(f"  already tracked as #{row['id']} ({row['status']}); resuming at the first missing step")
        elif not host_of(url):
            say("  not a URL; skipping")
            continue
        process(app, phases, args)
        if not args.dry_run:
            print_app_report(app)
        apps.append(app)
    return finish(apps, args)


def host_of(url: str) -> str:
    return urlsplit(url).netloc


def scan() -> list[App]:
    rows = tracker.load()
    apps_dir = root() / "applications"
    apps = [app_from_folder(p, rows) for p in sorted(apps_dir.glob("*")) if p.is_dir()] if apps_dir.is_dir() else []
    matched = {a.row_id for a in apps if a.row_id}
    for r in rows:  # tracker rows with no folder on disk
        if r["id"] in matched or r["status"].startswith("skipped"):
            continue
        apps.append(App(url=r["url"], company=r["company"], role=r["role"], location=r["location"],
                        ats=r["ats"], status=r["status"], row_id=r["id"],
                        folder=Path(r["folder"]) if r["folder"] and Path(r["folder"]).is_dir() else None))
    return apps


def cmd_audit(args) -> int:
    apps = scan()
    if not apps:
        say("No applications found.")
        return 0
    short = lambda a: (a.folder.name[11:] if a.folder else a.label)[:46]  # noqa: E731
    say(f"{'application':<48}{'status':<18}" + "".join(f"{p:<10}" for p in PHASES))
    bad = 0
    detail = []
    for a in apps:
        todo = needed_phases(a, refill=True)
        cells = []
        for p in PHASES:
            applies = not (a.status.startswith("skipped") and p in ("fill", "contacts"))
            cells.append(f"{'-' if not applies else ('MISSING' if p in todo else 'ok'):<10}")
        say(f"{short(a):<48}{(a.status or 'untracked')[:17]:<18}" + "".join(cells))
        text = read_text(a.file("job.md")).lower()
        warn = ["job.md is a paraphrase, not the posting text"] if "paraphras" in text else []
        if todo or warn:
            bad += bool(todo)
            detail.append((a, todo, warn))
    if detail:
        say("\nDetails")
        for a, todo, warn in detail:
            say(f"  {short(a)}")
            for phase, problems in todo.items():
                say(f"    {phase}: {'; '.join(problems)}")
            for w in warn:
                say(f"    warning: {w}")
    missing = {p: sum(1 for a in apps if p in needed_phases(a, refill=True)) for p in PHASES}
    say("\n" + (f"{bad} of {len(apps)} applications are incomplete ("
                + ", ".join(f"{p}: {n}" for p, n in missing.items() if n) + ")."
                if bad else f"All {len(apps)} applications pass every check."))
    if bad:
        say("Run `python apply.py backfill` to run the missing contacts and log steps.")
    return 1 if bad else 0


def cmd_backfill(args) -> int:
    phases = parse_phases(args.only, default=("contacts", "log"))
    candidates = [a for a in scan() if not (args.company and args.company.lower() not in a.company.lower())]
    candidates.sort(key=lambda a: (a.company.lower(), str(a.folder)))  # same company together, so contacts get reused
    apps = []
    for app in candidates:
        if not needed_phases(app, phases):
            continue
        say(f"\n{app.label}")
        process(app, phases, args)
        if not args.dry_run:
            print_app_report(app)
        apps.append(app)
    if not apps:
        say("Nothing to backfill: every application passes the checks for " + ", ".join(phases) + ".")
        return 0
    return finish(apps, args)


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--only", help=f"comma-separated steps to run ({', '.join(PHASES)})")
    common.add_argument("--retries", type=int, default=1, help="extra attempts per step (default 1)")
    common.add_argument("--timeout", type=int, default=40, help="minutes per agent call (default 40)")
    common.add_argument("--budget", type=float, default=5.0, help="max USD per agent call (default 5)")
    common.add_argument("--linkedin-delay", type=int, default=45,
                        help="seconds between LinkedIn searches (default 45)")
    common.add_argument("--model", help="model alias or name for the agents")
    common.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"])
    common.add_argument("--permission-mode", default="auto",
                        choices=["acceptEdits", "auto", "bypassPermissions", "dontAsk"],
                        help="permission mode for the agents (default auto)")
    common.add_argument("--no-chrome", action="store_true", help="don't pass --chrome to the agents")
    common.add_argument("--dry-run", action="store_true", help="show which steps would run and stop")
    common.add_argument("--force", action="store_true",
                        help="re-run skipped or already-sent applications too")

    parser = argparse.ArgumentParser(description="Run every job-apply step for every application.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run", parents=[common], help="apply to job links, all steps")
    p.add_argument("urls", nargs="*")
    p.add_argument("--file", help="text file with one job link per line")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("audit", help="list missing steps for every application")
    p.set_defaults(func=cmd_audit)
    p = sub.add_parser("backfill", parents=[common], help="run missing steps for existing applications")
    p.add_argument("--company", help="only applications whose company contains this text")
    p.set_defaults(func=cmd_backfill)
    return parser


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
