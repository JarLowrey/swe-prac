"""Build the Jobs section of the site (the root build.py calls this; it can also run alone).

    python jobs/build.py --out site/jobs

It copies the page (web/), the tracker's Python (tracker/, which the page runs in Pyodide) and
zips the Claude Code skills kit (job-search/) into job-search.zip for visitors to download. The
page loads Pyodide from ../practice/vendor/, so build the practice section next to it.

The zip takes only the kit's tracked parts, named below, so a reference/ or applications/ folder
with someone's own data in it can never end up on the site.
"""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEB = HERE / "web"
TRACKER = HERE / "tracker"
KIT = HERE / "job-search"

TRACKER_FILES = ("job_tracker.py", "gmail_message.py", "tracker_api.py")
# Everything the zip holds, relative to the kit. Folders are taken whole, less SKIP.
KIT_PARTS = (".claude/skills", "examples", ".vscode/settings.json", ".gitignore", "README.md", "profile.schema.json")
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache"}
SKIP_NAMES = {"settings.local.json", ".DS_Store", "Thumbs.db"}


def kit_files() -> list[Path]:
    """The kit's files that go in the zip, relative to the kit, sorted."""
    files: list[Path] = []
    for part in KIT_PARTS:
        path = KIT / part
        if path.is_file():
            files.append(Path(part))
            continue
        if not path.is_dir():
            raise SystemExit(f"The kit is missing {part}")
        for f in path.rglob("*"):
            rel = f.relative_to(KIT)
            if f.is_file() and not SKIP_DIRS & set(rel.parts) and f.name not in SKIP_NAMES and f.suffix != ".pyc":
                files.append(rel)
    return sorted(files, key=lambda p: p.as_posix())


def write_kit(dest: Path) -> int:
    """Zip the kit under a job-search/ folder. Returns the number of files."""
    files = kit_files()
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files:
            info = zipfile.ZipInfo(f"job-search/{rel.as_posix()}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, (KIT / rel).read_bytes())
    return len(files)


def build(out: Path) -> None:
    """Write the Jobs section to `out` (replacing what's there)."""
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(WEB, out)
    (out / "py").mkdir()
    for name in TRACKER_FILES:
        shutil.copy(TRACKER / name, out / "py" / name)
    write_kit(out / "job-search.zip")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=HERE.parent / "site" / "jobs")
    args = parser.parse_args()
    build(args.out)
    print(f"OK: Jobs written to {args.out}")


if __name__ == "__main__":
    main()
