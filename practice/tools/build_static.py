"""Build the site: the whole app, which runs in the browser with no server behind it.

    python tools/build_static.py            # writes site/ (in practice/)
    python tools/build_static.py --serve    # ...then serves it at http://127.0.0.1:8765/
    python tools/build_static.py --out dist

The repo root's build.py calls build() for site/practice/, next to the Jobs section, which
loads Pyodide from this section's vendor/.

The output is static files: the frontend (swe_prac/static/), data.json (every question, study
page and review text, pre-rendered), each problem's tests, the test runner, and the two
WebAssembly runtimes the browser runs your code with: Pyodide (CPython) and ruff. GitHub Pages
publishes it as it is; locally, --serve hands the files to the browser (it runs nothing itself).

The runtimes come from npm at the versions pinned below, checked against their published
SHA-512 and kept in .cache/ so later builds work offline.

Everything the browser can run is in the output, so the hidden tests are too (tests/), as are
the reference solutions and designs (data.json). The app shows hidden tests as counts only, but
anyone who opens those files can read them.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import copy
import functools
import hashlib
import http.server
import io
import json
import shutil
import sys
import tarfile
import threading
import tomllib
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from swe_prac import algorithms, config, designs, pages, problems, tech  # noqa: E402

CACHE_DIR = ROOT / ".cache" / "vendor"

# npm packages unpacked into site/vendor/<name>/: only the files the browser loads.
RUNTIMES = {
    "pyodide": {
        "package": "pyodide",
        "version": "314.0.8",
        "integrity": "sha512-74Wq1kXOC+CCEzAfxuRAO701nAcCMLjf8NrwvWpu8S41dVMXwXmLQ"
        "05dYB+F4e46AdnGo0oq7YHSVUpHsoarLQ==",
        "files": [
            "pyodide.mjs",
            "pyodide.asm.mjs",
            "pyodide.asm.wasm",
            "python_stdlib.zip",
            "pyodide-lock.json",
        ],
        "notice": "Pyodide {version} (https://pyodide.org), CPython 3.14 compiled to WebAssembly.\n"
        "Mozilla Public License 2.0 (https://github.com/pyodide/pyodide/blob/main/LICENSE).\n"
        "py-worker.js loads it to run your code.\n",
    },
    "ruff": {
        "package": "@astral-sh/ruff-wasm-web",
        "version": "0.17.4",  # the ruff version in requirements.txt
        "integrity": "sha512-2ZY4os1yTM7FVDWsQ1x8pRxuUQVf1mik0YxPDEqMM4KlbjgUnLv5o"
        "MvJ3DonigUw0lgBsofdhS8fsJW34UmiFg==",
        "files": ["ruff_wasm.js", "ruff_wasm_bg.wasm", "LICENSE"],
        "notice": "ruff {version} (https://github.com/astral-sh/ruff) compiled to WebAssembly,\n"
        "MIT licensed: see LICENSE. lint.js loads it for lint and Format.\n",
    },
}


# -- runtimes ----------------------------------------------------------------------------
def _tarball(spec: dict) -> bytes:
    """The package's npm tarball, from .cache/ or the registry, checked against its SHA-512."""
    name = spec["package"].rsplit("/", 1)[-1]
    cached = CACHE_DIR / f"{name}-{spec['version']}.tgz"
    if cached.exists():
        data = cached.read_bytes()
    else:
        url = f"https://registry.npmjs.org/{spec['package']}/-/{name}-{spec['version']}.tgz"
        print(f"Downloading {url}")
        with urllib.request.urlopen(url, timeout=120) as res:  # noqa: S310 - a fixed https URL
            data = res.read()
    algo, _, expected = spec["integrity"].partition("-")
    actual = base64.b64encode(hashlib.new(algo, data).digest()).decode()
    if actual != expected:
        raise SystemExit(f"{spec['package']} {spec['version']}: the download's {algo} is wrong")
    if not cached.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(data)
    return data


def write_runtime(name: str, out: Path) -> None:
    spec = RUNTIMES[name]
    dest = out / "vendor" / name
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(_tarball(spec)), mode="r:gz") as tar:
        for file in spec["files"]:
            member = tar.extractfile(f"package/{file}")
            (dest / file).write_bytes(member.read())
    (dest / "README.txt").write_text(spec["notice"].format(**spec), encoding="utf-8")


# -- lint settings -----------------------------------------------------------------------
def ruff_settings(path: Path) -> dict:
    """A ruff config file as the one settings object ruff's WebAssembly build takes. It can't
    read files, so an `extend`ed parent is merged in here: the child's keys win, and its
    lint.ignore adds to the parent's (as ruff applies rule selection down the chain)."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    parent = data.pop("extend", None)
    if parent is None:
        return data
    merged = copy.deepcopy(ruff_settings(path.parent / parent))
    lint = data.pop("lint", {})
    if {"select", "extend-select"} & set(lint):
        raise SystemExit(f"{path.name}: merging a child's select isn't supported; update build")
    merged.setdefault("lint", {})["ignore"] = [
        *merged["lint"].get("ignore", []),
        *lint.pop("ignore", []),
    ]
    merged["lint"].update(lint)
    merged.update(data)
    return merged


# -- data --------------------------------------------------------------------------------
def design_bundle() -> dict:
    """The system design section: questions with their review material, and the framework."""
    framework = designs.framework() if (config.DESIGNS_DIR / "framework.json").exists() else {}
    return {
        "questions": [
            {
                "question": q.public(),
                "hints": q.hints(),
                "key_points": list(q.key_points),
                "reference_html": designs.reference_html(q),
            }
            for q in designs.list_questions()
        ],
        "steps": framework.get("steps", []),
        "checklist": framework.get("checklist", []),
        "time_limit": config.DESIGN_TIME_LIMIT_SECONDS,
        "guide_html": designs.guide_html("framework"),
        "walkthrough_html": designs.guide_html("walkthrough"),
    }


def algo_bundle() -> dict:
    """The algorithms track: each problem's question (shown examples only) and study material.
    The tests are in tests/algo/<id>.json."""
    found = algorithms.list_problems()
    return {
        "problems": [
            {
                "problem": p.public(),
                "statement_html": algorithms.statement_html(p),
                "params": algorithms.param_names(p),
                "examples": algorithms.shown_cases(p),
                "starter_code": algorithms.starter_code(p),
                "scratch_starter": algorithms.scratch_starter(p),
                "hints_html": algorithms.hints_html(p),
                "explanation_html": algorithms.explanation_html(p),
                "foundations": algorithms.foundation_links(p),
            }
            for p in found
        ],
        "minutes": config.ALGO_MINUTES,
        "patterns": sorted({pattern for p in found for pattern in p.patterns}),
    }


def foundations_bundle() -> dict:
    """The study pages of each track (the foundations pages, and the tech investigations): the
    cards for its index and every page's payload, plus each tech project's files."""
    out = {}
    for track, folder in (
        ("design", designs.foundations_dir()),
        ("algo", algorithms.foundations_dir()),
    ):
        found = pages.list_pages(folder)
        out[track] = {
            "cards": [p.card() for p in found],
            "pages": {p.slug: pages.payload(folder, p.slug) for p in found},
        }
    out["tech"] = tech.bundle()
    return out


def bundle() -> dict:
    """data.json: everything the pages show, keyed by problem id. Tests are separate files."""
    out = []
    for problem in problems.list_problems():
        out.append(
            {
                "problem": problem.public(),
                "levels": [
                    {
                        "level": lv,
                        "title": problem.level_title(lv),
                        "statement_html": problems.statement_html(problem, lv),
                        "stubs": problems.level_stubs(problem, lv),
                    }
                    for lv in config.LEVELS
                ],
                # tests.py as the editor shows it once level N is unlocked (shown tests only).
                "tests_source": {
                    str(lv): problems.shown_tests_source(problem, lv) for lv in config.LEVELS
                },
                "starter_code": problems.starter_code(problem),
                "scratch_starter": problems.scratch_starter(problem),
                "hints_html": problems.review_html(problem, "hints"),
                "analysis_html": problems.review_html(problem, "analysis"),
                "reference_code": problems.reference_code(problem),
            }
        )
    return {
        "problems": out,
        "conventions_html": problems.conventions_html(),
        "time_limit": config.TIME_LIMIT_SECONDS,
        "pacing": config.PACING_SECONDS,
        "levels": list(config.LEVELS),
        "design": design_bundle(),
        "algo": algo_bundle(),
        "foundations": foundations_bundle(),
        "ruff": {
            "coding": ruff_settings(config.USER_RUFF_CONFIG),
            "algo": ruff_settings(config.ALGO_RUFF_CONFIG),
        },
    }


def test_files() -> dict[str, dict]:
    """Every problem's tests, shown and hidden, as the runner takes them: {path: content}.
    The browser fetches a problem's file when you first run it."""
    out = {}
    for problem in problems.list_problems():
        tests = problems.tests(problem, len(config.LEVELS), include_hidden=True)
        out[f"tests/coding/{problem.id}.json"] = {"class_name": problem.class_name, "tests": tests}
    for problem in algorithms.list_problems():
        out[f"tests/algo/{problem.id}.json"] = {
            "class_name": "Solution",
            "tests": algorithms.tests(problem, include_hidden=True),
            "options": problem.runner_options(),
        }
    return out


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def build(out: Path, runtimes: bool = True) -> None:
    """Write the site to `out`. runtimes=False leaves out Pyodide and ruff (tests use it)."""
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(config.STATIC_DIR, out)
    _write_json(out / "data.json", bundle())
    for rel, data in test_files().items():
        _write_json(out / rel, data)
    (out / "py").mkdir()
    shutil.copy(config.RUNNER_PATH, out / "py" / "runner.py")
    shutil.copy(config.SCRATCH_HELPERS_PATH, out / "py" / "helpers.py")
    if runtimes:
        for name in RUNTIMES:
            write_runtime(name, out)
    (out / ".nojekyll").write_text("", encoding="utf-8")  # serve files as they are


# -- serving -----------------------------------------------------------------------------
class _NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    """Static files only. Revalidated on every load, so a rebuild shows up on refresh."""

    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".wasm": "application/wasm",
        ".json": "application/json",
    }

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - the base class's name
        pass


def serve(out: Path, port: int, open_browser: bool) -> None:
    handler = functools.partial(_NoCacheHandler, directory=str(out))
    for candidate in range(port, port + 20):
        try:
            server = http.server.ThreadingHTTPServer(("127.0.0.1", candidate), handler)
            break
        except OSError:
            continue
    else:
        raise SystemExit(f"No free port in {port}-{port + 19}.")
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Serving {out} at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    with contextlib.suppress(KeyboardInterrupt):
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=ROOT / "site")
    parser.add_argument("--serve", action="store_true", help="serve the site after building it")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="with --serve: don't open it")
    args = parser.parse_args()
    build(args.out)
    print(f"OK: site written to {args.out}")
    if args.serve:
        serve(args.out, args.port, not args.no_browser)


if __name__ == "__main__":
    main()
