# Job search

Live: https://jarlowrey.github.io/swe-prac/jobs/

Two tools for the job search, on one page of the site:

- **Tracker** (`#/`): finds your job applications in your Gmail and shows each one with the status
  from the company's latest email (applied, assessment, scheduling, interviewing, offer,
  rejected, ...), a chart of applications over time, the flow of statuses, and each application's
  email trail. Statuses come from rules in Python, not AI. You can set a status yourself, hide
  something that isn't an application, and hand any application to a Claude skill.
- **Claude skills** (`#/skills`): four [Claude Code](https://code.claude.com/docs/en/overview) skills
  that do the busywork of applying. For each one the page says what it does and what it needs
  before you start, takes the details, and builds the prompt to copy into Claude Code. The page
  never runs a skill: Claude Code does, on your computer, with your Claude plan.

## How it works without a server

**Gmail.** Each visitor makes a Google sign-in client in a Google Cloud project of their own (the
Connect Gmail page, `#/gmail`, walks through it: about ten minutes, free) and pastes its client ID
into the page. The page asks Google for a read-only token (`gmail.readonly`) with Google Identity
Services, then calls the Gmail REST API straight from the browser. The token lives in memory for
an hour and is never stored. Nobody's mail passes through anyone else's app or server.

- The app stays in Google's **Testing** mode with the visitor as its only test user, so Google
  shows an "unverified app" warning (expected: the app is theirs) and asks for consent again
  every 7 days.
- Gmail allows about 100 full messages a minute per user, so the first sync of a few hundred
  emails takes a few minutes. `gmail.js` paces itself under that, waits when Gmail says to slow
  down, and skips messages it already has, so later syncs only fetch what's new and a stopped
  sync picks up where it left off.

**Sorting the mail.** `tracker/job_tracker.py` runs in the page in Pyodide (CPython in
WebAssembly, the same build the practice section uses), in a Web Worker. `gmail_message.py`
turns Gmail's raw messages into records, and `tracker_api.py` is the JSON-in, JSON-out surface
the page calls.

**Storage.** Mail, applications, settings and the statuses you set stay in the browser's
IndexedDB (database `swe-prac-jobs`). Export and Import (on the Connect Gmail page) move them
between browsers; the export holds the full text of your job emails, so keep it private.

**Claude.** A static page can't drive Claude Code or your browser, so it hands off a prompt. The
skills that fill forms and search LinkedIn need Claude in Chrome connected to Claude Code
(`/chrome`, or `claude --chrome`), which takes a Pro, Max, Team or Enterprise plan.

## Layout

```
web/          the page: jobs.js (router), tracker.js, skills.js + prompts.js, setup.js (Gmail
              setup, settings, export/import), gmail.js (sign-in and the paced sync), store.js
              (IndexedDB), python.js + tracker-worker.js + tracker-py.js (Pyodide), ui.js, jobs.css
tracker/      job_tracker.py (the rules; also a command-line tool), gmail_message.py, tracker_api.py
job-search/   the Claude Code skills kit, zipped into the site as job-search.zip (see its README)
tests/        Python tests; tests/js/ runs the built page's modules and the tracker in Pyodide in Node
build.py      writes site/jobs/ (the root build.py calls it)
```

The tracker also runs on its own, on a file the page's Export button saved:

```
python jobs/tracker/job_tracker.py scan job-tracker-2026-11-26.json --since 2026-09-01 --format csv
```

## Rules for this folder

- No real people's names or email addresses, and no real employers, in code, tests, examples or
  docs: use `example.com` / `.example` addresses and fictional companies (Northwind, Contoso,
  Fabrikam, ...).
- Services the tools depend on can be named (Gmail, LinkedIn, the applicant tracking systems).
  Coding-assessment platforms are not named: the tracker learns them from the "Assessment and
  interview services" setting, which each visitor fills in.
- Personal job-search data never goes in the repo. The kit's `.gitignore` keeps out its
  `reference/`, `applications/`, `guides/` and `tracker.csv`, the root `.gitignore` keeps out
  `emails*.json`, `applications*.json` and exports, and `build.py` zips the kit from a fixed list
  of its parts, so a personal folder in it never reaches the site.

## Tests

From the repo root, after `python build.py`:

```
.venv\Scripts\python -m unittest discover -s jobs\tests   # the rules, the Gmail parsing, the build and the zip
node --test "jobs/tests/js/*.test.mjs"                     # the tracker in Pyodide, the prompts, the paced sync
```
