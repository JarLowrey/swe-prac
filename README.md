# SWE Practice

Live site: https://jarlowrey.github.io/swe-prac/

Practice for software engineering interviews, and tools for the job search around them. Both run
entirely in the browser: no account, no server, and what you do stays in your browser.

| Section | On the site | In the repo |
| --- | --- | --- |
| **Interview practice**: timed multi-level coding problems, algorithm problems and system design rounds, with foundations pages to study from and tech investigations | [/practice/](https://jarlowrey.github.io/swe-prac/practice/) | [practice/](practice/README.md) |
| **Job search**: an application tracker that reads your job mail from Gmail, a Job finder that charts recent LinkedIn and Indeed postings, and five AI skills (find postings, fill in applications, draft answers, find people to contact, research an interview loop), each with a copyable prompt; and an Open jobs page for employers who want to post a position | [/jobs/](https://jarlowrey.github.io/swe-prac/jobs/) | [jobs/](jobs/README.md) |

## Layout

```
build.py      builds the whole site into site/ (gitignored); --serve serves it locally
home/         the landing page (site/index.html)
practice/     the interview practice app (site/practice/)
jobs/         the job tracker page, its Python and the AI skills kit (site/jobs/)
.github/      the workflow that tests and publishes site/ to GitHub Pages on every push to master
```

## Build and run locally

Python 3.12 or newer, and Node 22 or newer for the browser tests:

```
python -m venv .venv
.venv\Scripts\python -m pip install -r practice\requirements.txt
.venv\Scripts\python build.py --serve       # builds site/, opens http://127.0.0.1:8765/
```

The first build downloads Pyodide and ruff (WebAssembly) at pinned, hash-checked versions and
caches them in `practice/.cache/`. The Jobs section uses the same Pyodide, from
`site/practice/vendor/`.

## Tests

```
cd practice
..\.venv\Scripts\python -m unittest discover -s tests
node --test "tests/js/*.test.mjs"           # needs the built site; RUFF=..\.venv\Scripts\ruff.exe if ruff isn't on PATH
cd ..
.venv\Scripts\python -m unittest discover -s jobs\tests
node --test "jobs/tests/js/*.test.mjs"
```

Each section's README has the details.
