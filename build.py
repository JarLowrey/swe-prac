"""Build the whole site into site/: the landing page, the interview practice app and the Jobs section.

    python build.py                        # writes site/
    python build.py --serve                # ...then serves it at http://127.0.0.1:8765/
    python build.py --serve --no-browser

    site/index.html     the landing page (home/index.html)
    site/practice/      the practice app (practice/tools/build_static.py)
    site/jobs/          the job tracker and the AI skills (jobs/build.py)

Everything runs in the browser; GitHub Pages publishes site/ as it is.
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


practice = _load("build_static", ROOT / "practice" / "tools" / "build_static.py")
jobs = _load("jobs_build", ROOT / "jobs" / "build.py")


def build(out: Path = SITE, runtimes: bool = True) -> None:
    """Write the site to `out`. runtimes=False leaves out the runtimes (tests use it)."""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    practice.build(out / "practice", runtimes=runtimes)
    jobs.build(out / "jobs")
    shutil.copy(ROOT / "home" / "index.html", out / "index.html")
    (out / ".nojekyll").write_text("", encoding="utf-8")  # serve files as they are


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=SITE)
    parser.add_argument("--serve", action="store_true", help="serve the site after building it")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="with --serve: don't open it")
    args = parser.parse_args()
    build(args.out)
    print(f"OK: site written to {args.out}")
    if args.serve:
        practice.serve(args.out, args.port, not args.no_browser)


if __name__ == "__main__":
    main()
