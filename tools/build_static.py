"""Build the static site (GitHub Pages): the frontend plus a browser-side backend.

Code can't run on a static host, so Run, Submit, Run scratch, Format and lint are disabled there
(app.js checks `window.SWE_STATIC`). Everything else (sessions, the timer, pausing, review,
history, study pages) runs in the browser, with sessions kept in localStorage.

    python tools/build_static.py            # writes site/
    python tools/build_static.py --out dist

Only what the browser needs is exported: statements, stubs, the shown tests, the review texts and
the reference solution. Hidden tests are never written to the output.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from swe_prac import config, problems  # noqa: E402

STATIC_SITE_DIR = Path(__file__).resolve().parent / "static_site"


def bundle() -> dict:
    """Everything the in-browser backend serves, keyed by problem id."""
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
    }


def _replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"index.html needs exactly one {old!r}; update build_static.py")
    return text.replace(old, new)


def static_index() -> str:
    """index.html with relative URLs (a Pages site lives under /<repo>/) and the static backend."""
    html = (config.STATIC_DIR / "index.html").read_text(encoding="utf-8")
    html = _replace_once(
        html,
        'paths: { vs: "/static/vendor/monaco/vs" }',
        # Absolute, because Monaco derives its web-worker URLs from this path.
        'paths: { vs: new URL("vendor/monaco/vs", document.baseURI).href }',
    )
    html = _replace_once(
        html,
        '<script type="module" src="/static/app.js"></script>',
        '<script src="static-api.js"></script>\n  <script type="module" src="app.js"></script>',
    )
    return html.replace("/static/", "")


def build(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(config.STATIC_DIR, out)
    (out / "index.html").write_text(static_index(), encoding="utf-8")
    shutil.copy(STATIC_SITE_DIR / "static-api.js", out / "static-api.js")
    (out / "data.json").write_text(
        json.dumps(bundle(), separators=(",", ":"), ensure_ascii=False), encoding="utf-8"
    )
    (out / ".nojekyll").write_text("", encoding="utf-8")  # serve files as they are


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=ROOT / "site")
    args = parser.parse_args()
    build(args.out)
    print(f"OK: static site written to {args.out}")


if __name__ == "__main__":
    main()
