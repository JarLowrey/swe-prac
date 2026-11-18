"""Check the study content: the system design foundations pages and questions.

    python tools/check_content.py

It renders every markdown file the app shows and reports:
- data-structure diagram blocks that fail to render (```array, ```tree, ...),
- internal links (#/design/learn/<page>/<section>) whose target doesn't exist,
- design questions whose `foundations` references don't resolve,
- foundations pages without a summary paragraph or with duplicate section titles,
- mermaid labels that start like a markdown list ("1. step"), which mermaid draws as
  "Unsupported markdown: list",
- diagram captions over 100 characters (a caption is one line, and a long one makes the figure
  wide enough to shrink; docs/writing-content.md asks for about 70).

Otherwise Mermaid diagrams are drawn in the browser, so they are only checked there (a page with a
broken one shows a red "Diagram error" box).
Exit code 1 if anything is wrong.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from swe_prac import config, pages  # noqa: E402

LINK = re.compile(r'href="(#/[^"]*)"')

# Mermaid runs flowchart, subgraph and state labels through a markdown parser, and a label that
# starts like a list item ("1. read", "2) write", "- item") is drawn as the words "Unsupported
# markdown: list", without an error. Sequence diagrams and text after a <br/> are unaffected.
MERMAID_BLOCK = re.compile(r"^```mermaid[ \t]*\n(.*?)^```", re.S | re.M)
LIST_ITEM = re.compile(r"\s*(?:\d+[.)]|[-*+])\s")
QUOTED = re.compile(r'"([^"]*)"')
EDGE_TEXT = re.compile(r'\|([^|"]*)\|')  # -->|label|
NODE_TEXT = re.compile(r'\w[\w-]*\s*(?:\[\[|\[\(|\(\[|\(\(|\{\{|\[/|[\[({])\s*([^"\])}|][^\])}]*)')
SUBGRAPH_TITLE = re.compile(r"^\s*subgraph\s+(?!\w[\w-]*\s*[\[({])(.+)$")
STATE_TEXT = re.compile(r":\s*(.+)$")


def _mermaid_labels(line: str, state: bool) -> list[str]:
    """The label texts on one flowchart or state diagram line (best effort)."""
    labels = QUOTED.findall(line)
    bare = QUOTED.sub('""', line)  # so brackets inside quoted labels aren't read as shapes
    labels += EDGE_TEXT.findall(bare) + NODE_TEXT.findall(bare)
    title = SUBGRAPH_TITLE.match(bare)
    if title:
        labels.append(title.group(1))
    if state and (desc := STATE_TEXT.search(bare)):
        labels.append(desc.group(1))
    return labels


def check_mermaid(text: str, where: str, errors: list[str]) -> None:
    for block in MERMAID_BLOCK.finditer(text):
        body = block.group(1).strip()
        kind = body.split(None, 1)[0] if body else ""
        if not kind.startswith(("flowchart", "graph", "stateDiagram")):
            continue
        for line in body.splitlines()[1:]:
            bad = [t for t in _mermaid_labels(line, kind.startswith("state")) if LIST_ITEM.match(t)]
            if bad:
                errors.append(
                    f"{where}: mermaid label {bad[0].strip()[:40]!r} starts like a markdown list"
                    ' and is drawn as "Unsupported markdown: list"; write "(1) ..." or'
                    ' "Step 1: ..."'
                )


DS_BLOCK = re.compile(
    r"^```(?:array|tree|linkedlist|grid|intervals|ring)[ \t]*\n(.*?)^```", re.S | re.M
)
CAPTION = re.compile(r"^\s*caption:\s*(.*?)\s*$")
MAX_CAPTION = 100


def check_captions(text: str, where: str, errors: list[str]) -> None:
    for block in DS_BLOCK.finditer(text):
        for line in block.group(1).splitlines():
            m = CAPTION.match(line)
            if m and len(m.group(1)) > MAX_CAPTION:
                errors.append(
                    f"{where}: caption {m.group(1)[:40]!r}... is {len(m.group(1))} characters;"
                    f" keep captions under {MAX_CAPTION} (about 70 is best)"
                )


def check_source(text: str, where: str, errors: list[str]) -> None:
    """Checks on the markdown source: mermaid labels and diagram captions."""
    check_mermaid(text, where, errors)
    check_captions(text, where, errors)


def _sections(folder: Path) -> dict[str, set[str]]:
    out = {}
    for page in pages.list_pages(folder):
        ids = set()
        for s in page.sections():
            ids.add(s["id"])
            ids.update(c["id"] for c in s["children"])
        out[page.slug] = ids
    return out


def check_links(html: str, where: str, targets: dict, errors: list[str]) -> None:
    for href in LINK.findall(html):
        m = re.fullmatch(r"#/(design)/learn(?:/([\w-]+))?(?:/([\w-]+))?", href)
        if m:
            track, slug, section = m.groups()
            sections = targets[track]
            if slug and slug not in sections:
                errors.append(f"{where}: link to unknown page {href}")
            elif section and section not in sections[slug]:
                errors.append(f"{where}: link to unknown section {href}")


def check_html(html: str, where: str, targets: dict, errors: list[str]) -> None:
    for m in re.finditer(r'<div class="diagram-error"><strong>([^<]*)</strong>\s*([^<]*)', html):
        errors.append(f"{where}: {m.group(1)} {m.group(2).strip()}")
    check_links(html, where, targets, errors)


def check_pages(folder: Path, label: str, targets: dict, errors: list[str]) -> int:
    count = 0
    for page in pages.list_pages(folder):
        count += 1
        where = f"{label}/{page.path.name}"
        if not page.summary or page.summary.startswith("#"):
            errors.append(f"{where}: needs a one-paragraph summary right after the title")
        titles = [s["title"] for s in page.sections()]
        dupes = {t for t in titles if titles.count(t) > 1}
        if dupes:
            errors.append(f"{where}: duplicate section titles {sorted(dupes)}")
        check_source(page.path.read_text(encoding="utf-8"), where, errors)
        check_html(pages.page_html(page), where, targets, errors)
    return count


def main(argv: list[str]) -> int:
    which = set(argv) or {"designs"}
    errors: list[str] = []
    design_dir = config.DESIGNS_DIR / "foundations"
    targets = {"design": _sections(design_dir)}
    summary = []
    if "designs" in which:
        n = check_pages(design_dir, "designs/foundations", targets, errors)
        from swe_prac import designs

        for q in designs.list_questions():
            where = f"designs/{q.id}"
            reference = q.path / "reference.md"
            if reference.exists():
                check_source(reference.read_text(encoding="utf-8"), f"{where}/reference.md", errors)
            check_html(designs.reference_html(q), f"{where}/reference.md", targets, errors)
            data = json.loads((q.path / "design.json").read_text(encoding="utf-8"))
            for ref in data.get("foundations", []):
                slug, _, section = ref.partition("/")
                known = targets["design"].get(slug)
                if known is None or (section and section not in known):
                    errors.append(f"{where}/design.json: foundations link {ref!r} doesn't resolve")
        summary.append(f"{n} design foundations pages")
    for e in errors:
        print("ERROR", e)
    print(("FAILED: " if errors else "OK: ") + ", ".join(summary) + f" ({len(errors)} problems)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
