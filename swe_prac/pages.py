"""Foundations pages: long-form study material, one markdown file per page.

A track keeps its pages in <track dir>/foundations/NN_slug.md. The file starts with `# Title`
and a one-paragraph summary (shown on the page's card). Every `## Section` gets a stable id
(its slugified title) so other pages, hints and reviews can link to it with a route like
#/design/learn/<slug>/<section-id>.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import markdown as md
from markdown.extensions.toc import slugify

from . import diagrams


class PageNotFound(KeyError):
    pass


@dataclass(frozen=True)
class Page:
    slug: str
    title: str
    summary: str
    path: Path

    def sections(self) -> list[dict]:
        """The ## headings (with ### children), in order, with the ids the HTML will carry."""
        out: list[dict] = []
        seen: set[str] = set()
        in_code = False
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.startswith("```"):
                in_code = not in_code
            if in_code:
                continue
            m = re.match(r"^(##|###)\s+(.+?)\s*#*\s*$", line)
            if not m:
                continue
            title = _plain(m.group(2))
            entry = {"id": _unique(slugify(title, "-"), seen), "title": title}
            if m.group(1) == "##":
                out.append({**entry, "children": []})
            elif out:
                out[-1]["children"].append(entry)
        return out

    def card(self) -> dict:
        return {
            "slug": self.slug,
            "title": self.title,
            "summary": self.summary,
            "sections": [{"id": s["id"], "title": s["title"]} for s in self.sections()],
        }


def _plain(text: str) -> str:
    """Heading text without inline markdown, as the toc extension slugifies it."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return re.sub(r"[`*_]", "", text).strip()


def _unique(slug: str, seen: set[str]) -> str:
    base, n = slug, 0
    while slug in seen:
        n += 1
        slug = f"{base}_{n}"
    seen.add(slug)
    return slug


def _load(path: Path) -> Page:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\s*#\s+(.+?)\s*\n", text)
    if not m:
        raise ValueError(f"{path.name} must start with '# Title'")
    rest = text[m.end() :].lstrip("\n")
    summary = _plain(rest.split("\n\n", 1)[0].replace("\n", " "))
    slug = re.sub(r"^\d+_", "", path.stem).replace("_", "-")
    return Page(slug=slug, title=m.group(1).strip(), summary=summary, path=path)


def list_pages(folder: Path) -> list[Page]:
    if not folder.exists():
        return []
    return [_load(p) for p in sorted(folder.glob("*.md")) if re.match(r"\d+_", p.name)]


def get(folder: Path, slug: str) -> Page:
    for page in list_pages(folder):
        if page.slug == slug:
            return page
    raise PageNotFound(slug)


def render(text: str) -> str:
    """Markdown to HTML with heading ids and data-structure diagrams (mermaid stays a code
    block; the browser renders it)."""
    html = md.markdown(
        text,
        extensions=["fenced_code", "tables", "sane_lists", "toc"],
        extension_configs={"toc": {"slugify": slugify, "separator": "-", "toc_depth": "2-3"}},
    )
    return diagrams.render_blocks(html)


def page_html(page: Page) -> str:
    """The page body without its # title (the frontend shows the title in the page header)."""
    text = page.path.read_text(encoding="utf-8")
    body = re.sub(r"\A\s*#\s+.+\n", "", text, count=1)
    return render(body)


def payload(folder: Path, slug: str) -> dict:
    pages = list_pages(folder)
    for i, page in enumerate(pages):
        if page.slug == slug:
            return {
                **page.card(),
                "toc": page.sections(),
                "html": page_html(page),
                "prev": pages[i - 1].card() if i > 0 else None,
                "next": pages[i + 1].card() if i + 1 < len(pages) else None,
            }
    raise PageNotFound(slug)


def links(folder: Path, base: str, refs) -> list[dict]:
    """Resolve "page/section" (or "page") references to titled links under the route `base`.

    Unknown references are dropped, so the app never shows a dead link; the content checks
    (tools/check_content.py, run by the tests) report them instead.
    """
    by_slug = {p.slug: p for p in list_pages(folder)}
    out = []
    for ref in refs:
        slug, _, section = ref.partition("/")
        page = by_slug.get(slug)
        if page is None:
            continue
        titles = {}
        for s in page.sections():
            titles[s["id"]] = s["title"]
            titles.update({c["id"]: c["title"] for c in s["children"]})
        if section and section not in titles:
            continue
        out.append(
            {
                "page": slug,
                "section": section,
                "page_title": page.title,
                "title": titles.get(section, page.title),
                "href": f"{base}/{slug}" + (f"/{section}" if section else ""),
            }
        )
    return out
