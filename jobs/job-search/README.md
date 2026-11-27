# job-search

Five AI agent skills (SKILL.md) that do the busywork of finding and applying for software engineering jobs, plus the folder layout they read and write. They're part of the SWE Practice site: its **Jobs > AI skills** page takes your profile, explains each skill, and builds the prompt to paste into your AI agent. This folder is what that page's `job-search.zip` holds, plus `reference/profile.yaml` written from the page's profile form.

- **job-find**: searches LinkedIn and Indeed in your browser for jobs posted in the last day (or 3, 7 or 14) that match your target roles and locations, reading only the results pages, and keeps them in `postings.json`. Import that file on the site's **Jobs > Job finder** page to chart postings by day, company, workplace and pay. **It never applies or saves anything.**
- **job-apply**: paste one or more job links. For each, it reads the posting, checks the location against yours, fills the application in Chrome (contact details, work authorization, self-ID, resume upload), drafts written answers, finds people to contact, logs it in a tracker, and **stops before Submit** so you can review.
- **job-answers**: drafts answers to free-text questions and cover letters from your resume and your own reference docs. It only uses facts you've written down and leaves `[ADD: ...]` placeholders for anything it doesn't know.
- **job-contacts**: finds a recruiter, an engineer and the likely hiring manager on LinkedIn and drafts a connection note and follow-up for each. **It never sends anything.**
- **interview-prep**: researches how a company interviews (the loop, behavioral, coding and system design rounds) with four research agents, and writes a sourced study guide that maps likely behavioral questions onto your stories and links the SWE Practice study pages. On the Skills page, pick an application from your tracker to add what your emails say about the loop.

Finding postings, filling forms and searching LinkedIn need your agent connected to Chrome, signed in to your accounts. Reading reference docs from Google Drive needs Google Drive access for your agent. interview-prep writes its guide as a doc when your agent has a docs connector, and as a markdown file in `guides/` otherwise.

## Layout

```
skills/               the five skills, one SKILL.md folder each (tracked)
profile.schema.json    allowed values for the profile's fixed-answer fields (tracked)
examples/              fake data showing every file the skills read or write (tracked)
  reference/             profile template, a fictional resume, a brag doc,
                         behavioral stories and a design write-up
  applications/          one worked application: job.md, answers.md, contacts.md, fill-log.md
  tracker.csv            a sample tracker
  postings.json          sample job-find output (fictional companies, example.com links)

reference/             your profile, resume, stories and docs  ┐  gitignored:
applications/          one folder per job                      │  personal data stays
tracker.csv            your applications                       │  on your machine
guides/                interview study guides written as files │
postings.json          postings job-find found                 │
postings-raw/          job-find's per-search batch files       ┘
```

Everything personal lives in the gitignored paths. The skills and `examples/` contain no real names, contact details or employer material, so the repo is safe to push. Check `git status` before committing anyway.

## Setup

1. If you downloaded the kit from the Skills page, `reference/profile.yaml` already holds what you typed there; fill in anything still marked `TODO`. Otherwise copy the template into a `reference/` folder and fill it in:
   ```sh
   mkdir -p reference && cp examples/reference/profile.yaml reference/
   ```
   Work through every value: identity, acceptable locations, target roles, work authorization and the voluntary self-ID answers (`decline` is always fine). Fixed-answer fields take a key such as `us_citizen` or `not_a_protected_veteran` rather than free text, and yes/no answers are `true` / `false`; the allowed keys are listed in the example and defined in `profile.schema.json`. With the [YAML extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) installed, VS Code validates your profile against that schema and offers the choices as you type. The skills won't fill a form while the profile still has the example's values.
2. Put your resume PDF in `reference/` and point `resume.path` at it. The file is uploaded as-is, so name it the way you want employers to see it.
3. Put material for written answers in `reference/` too: a brag doc (your wins, with numbers), a career summary with specific project details and designs, behavioral stories (situation, the actions you took, result, lesson) and high-level project write-ups. Markdown, PDF, .txt and .docx all work. See `examples/reference/` for the shape. Google Docs can go in `reference_docs` instead.
4. Start your AI agent in this folder and point it at `skills/`, or copy those folders to where your agent looks for skills.

### Using the skills from any folder

To use the skills from any folder, link them into your agent's personal skills folder and keep this folder at `~/job-search` (or set `JOB_SEARCH_DIR` to wherever it is). Set the first line to your agent's personal skills folder:

```powershell
# Windows (junctions need no admin rights)
$skills = "$HOME\path\to\agent\skills"
foreach ($s in "job-find", "job-apply", "job-answers", "job-contacts", "interview-prep") {
  New-Item -ItemType Junction -Path "$skills\$s" -Target "$PWD\skills\$s"
}
```

```sh
# macOS / Linux
skills=~/path/to/agent/skills
for s in job-find job-apply job-answers job-contacts interview-prep; do ln -s "$PWD/skills/$s" "$skills/$s"; done
```

## Use

- `/job-find` or "Find backend jobs posted this week in Denver": job-find searches both sites and updates `postings.json`; `python skills/job-find/scripts/postings.py list --days 7` shows them, and `JOB_SEARCH_DIR=examples` lists the sample.
- "Apply to these: \<link\> \<link\>": runs job-apply for each link and leaves each tab open on the filled form.
- "Draft answers for these questions: ...": job-answers on its own.
- "Find me people to talk to at Northwind about the payments role": job-contacts on its own.
- "I submitted the Northwind one" / "What have I applied to?": tracker updates and listing.
- `/interview-prep Northwind`: a study guide for Northwind's interviews. The Skills page's prompt adds the role, status and your email context.

The Skills page builds each of these prompts from what you type, so you don't have to remember the wording.

### Batches that can't skip a step

Working through several links in one conversation lets steps slip (the form gets filled, the LinkedIn contacts don't). `apply.py` runs each step as its own short, headless agent and then checks the file the step must leave behind. It needs an agent that runs from the command line without a chat window (below). Anything missing is retried, then reported as FAILED. The tracker row is written by the script, not left to an agent.

```sh
python skills/job-apply/scripts/apply.py run <link> <link> ...   # read, fill, contacts, log for each
python skills/job-apply/scripts/apply.py audit                   # which applications are missing which step
python skills/job-apply/scripts/apply.py backfill                # run the missing contacts and tracker steps
```

| Step | Leaves behind | Done when |
|---|---|---|
| read | `job.md` | at least 500 characters, in an application folder |
| fill | `fill-log.md`, plus `answers.md` if the form had written questions | both exist |
| contacts | `contacts.md` | has the `# Contacts` heading and a connection note, or says nobody suitable was found |
| log | a row in `tracker.csv` | the row has a folder and a status |

**Set up your agent first.** Set `JOB_SEARCH_AGENT` to the command that runs your agent non-interactively, with access to your Chrome, as a JSON list. Each step's prompt goes to it on stdin, or in place of a `"{prompt}"` argument if the command has one. The agent must print its answer on stdout, ending with the JSON object the prompt asks for.

```sh
export JOB_SEARCH_AGENT='["my-agent", "--headless", "{prompt}"]'   # PowerShell: $env:JOB_SEARCH_AGENT = '...'
```

- **Safe to re-run.** A step whose check already passes is skipped, so re-running the same command after a failure only does the missing work. `--dry-run` shows what would run.
- **A blocked form doesn't stop the contacts step.** Sign-in pages, CAPTCHAs and the like leave the application `in-progress` with what you need to do listed.
- **One agent at a time**, because they share your Chrome. `--linkedin-delay` (default 45 seconds) spaces out the LinkedIn searches.
- **Nobody can answer prompts**, so a site Chrome hasn't been approved for fails that step instead of waiting. The report includes the denial; approve the site and re-run.
- **Options:** `--only read,fill` (or `contacts,log`, ...) to run some steps, `--retries`, `--timeout` (minutes per step, default 40). Run with `-h` for the rest.

The tracker is a plain CSV that opens in Excel. You can also run the script directly:

```sh
python skills/job-apply/scripts/tracker.py list
JOB_SEARCH_DIR=examples python skills/job-apply/scripts/tracker.py list   # the sample data
```

## How the skills find your data

They look for the job-search folder in this order: `$JOB_SEARCH_DIR`, then the current directory if it contains `reference/profile.yaml`, then `~/job-search`. The tracker script also checks the repo it lives in. Relative paths in the profile (resume, reference folder) are resolved against that folder.

## Ground rules the skills follow

- Never click the final Submit button, and never tick terms, privacy-policy or attestation boxes. You do those. The only consents the skills answer for you are the SMS-contact and AI-review ones you set in `consents` in your profile.
- Never send LinkedIn requests or messages, and keep LinkedIn browsing light (about 6–8 page loads per company).
- When the profile or resume doesn't answer a form question, leave it blank and list it for you rather than guess.
- Questions that carry an anti-AI instruction ("start with the word kiwi", "answer in all lowercase") get a draft in `answers.md`, but the skills never type them into the form. You enter those yourself.
- Keep employer-confidential detail from reference docs out of drafted answers.
