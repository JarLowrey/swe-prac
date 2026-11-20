"""HTTP API for the tech investigations, mounted under /api/tech.

An investigation is one study page, tech/NN_slug.md (read by pages.py, like the foundations
pages), about a small project in the folder next to it named after the page's slug
(tech/01_react_swapi.md explains tech/react-swapi/). The page shows the project's files with
```include blocks, so what you read is the code that runs, and /files lists the whole finished
project for the file browser. There are no sessions or spoilers: it's study material only.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from . import config, pages

router = APIRouter(prefix="/api/tech")

# Never part of the source: installed packages, build output, caches. A project's own
# .gitignore adds to this list.
SKIP_DIRS = {
    "node_modules", "dist", "build", "coverage", ".git", ".vite", ".next", ".turbo",
    "__pycache__", ".venv", ".pytest_cache", ".ruff_cache", ".mypy_cache",
}  # fmt: skip
# Local secrets stay out even when a .gitignore forgets them: the static site publishes every
# file listed here.
SKIP_FILES = {".env", ".env.*", "*.local", ".DS_Store", "Thumbs.db"}
KEEP_FILES = {".env.example"}
# Bigger files (lock files, mostly) are listed without their text.
MAX_TEXT_BYTES = 100_000

# The file browser's language for each extension, on top of the ```include ones; the browser
# colours these (common.js).
LANGUAGES = {**pages.CODE_LANGUAGES, ".mjs": "js", ".cjs": "js", ".mts": "ts", ".svg": "html"}


def pages_dir() -> Path:
    return config.TECH_DIR


def project_dir(page: pages.Page) -> Path | None:
    folder = pages_dir() / page.slug
    return folder if folder.is_dir() else None


def _ignore_patterns(root: Path) -> list[str]:
    """The simple patterns of the project's .gitignore: names and globs like node_modules,
    *.log or /dist/ (negations aren't supported, so they are skipped)."""
    path = root / ".gitignore"
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "!")):
            out.append(line.strip("/"))
    return out


def _ignored(rel: str, patterns: list[str]) -> bool:
    """Whether a project-relative path (a/b/c.ts) matches a .gitignore pattern: by name for a
    pattern without a slash, else by the whole path."""
    name = rel.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(rel if "/" in pattern else name, pattern) for pattern in patterns)


def _source_files(root: Path) -> list[Path]:
    """The project's files, sorted by path, without the skipped folders and files. Symbolic
    links are left out, so nothing outside the folder is listed."""
    patterns = _ignore_patterns(root)
    found = []
    for folder, dirs, files in os.walk(root):
        base = Path(folder)
        rel_base = base.relative_to(root).as_posix()
        prefix = "" if rel_base == "." else rel_base + "/"
        dirs[:] = [
            d
            for d in dirs
            if d not in SKIP_DIRS
            and not (base / d).is_symlink()
            and not _ignored(prefix + d, patterns)
        ]
        for name in files:
            path = base / name
            skipped = name not in KEEP_FILES and any(fnmatch.fnmatch(name, p) for p in SKIP_FILES)
            if skipped or path.is_symlink() or _ignored(prefix + name, patterns):
                continue
            found.append(path)
    return sorted(found, key=lambda p: p.relative_to(root).as_posix())


def _file(path: Path, rel: str, sections: list[dict]) -> dict:
    size = path.stat().st_size
    entry = {
        "path": rel,
        "size": size,
        "lang": LANGUAGES.get(path.suffix.lower(), ""),
        "sections": sections,
        "text": None,
        "note": None,
    }
    if size > MAX_TEXT_BYTES:
        entry["note"] = f"This file is {size / 1024:.1f} KB, too big to show here."
        return entry
    try:
        entry["text"] = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        entry["note"] = "This is a binary file, so it isn't shown here."
    return entry


def project(page: pages.Page) -> dict | None:
    """The page's project for the file browser: every source file with its text, and the
    sections of the page that explain it. None if the page has no project folder."""
    root = project_dir(page)
    if root is None:
        return None
    root = root.resolve()
    explained: dict[str, list[dict]] = {}
    for name, section in page.includes():
        path = (pages_dir() / name).resolve()
        if section and path.is_relative_to(root):
            found = explained.setdefault(path.relative_to(root).as_posix(), [])
            if section not in found:
                found.append(section)
    files = []
    for path in _source_files(root):
        rel = path.relative_to(root).as_posix()
        files.append(_file(path, rel, explained.get(rel, [])))
    return {"slug": page.slug, "title": page.title, "folder": root.name, "files": files}


def card(page: pages.Page) -> dict:
    """The page's card, plus its project folder and file count (or None) for the links to the
    file browser."""
    root = project_dir(page)
    info = {"folder": root.name, "files": len(_source_files(root))} if root else None
    return {**page.card(), "project": info}


def page_payload(slug: str) -> dict:
    page = pages.get(pages_dir(), slug)
    return {**pages.payload(pages_dir(), slug), "project": card(page)["project"]}


def bundle() -> dict:
    """What tools/build_static.py publishes for the static site: what this API would serve."""
    found = pages.list_pages(pages_dir())
    return {
        "cards": [card(p) for p in found],
        "pages": {p.slug: page_payload(p.slug) for p in found},
        "projects": {p.slug: info for p in found if (info := project(p)) is not None},
    }


@router.get("/pages")
def list_pages() -> dict:
    return {"pages": [card(p) for p in pages.list_pages(pages_dir())]}


@router.get("/pages/{slug}")
def get_page(slug: str) -> dict:
    try:
        return page_payload(slug)
    except pages.PageNotFound:
        raise HTTPException(404, f"Unknown page {slug!r}") from None


@router.get("/pages/{slug}/files")
def get_files(slug: str) -> dict:
    try:
        info = project(pages.get(pages_dir(), slug))
    except pages.PageNotFound:
        raise HTTPException(404, f"Unknown page {slug!r}") from None
    if info is None:
        raise HTTPException(404, f"Page {slug!r} has no project folder")
    return info
