"""Check the study content: foundations pages, design questions, algorithm problems and the
tech investigations.

    python tools/check_content.py          # everything
    python tools/check_content.py designs  # one track: designs | algorithms | tech

It renders every markdown file the app shows and reports:
- data-structure diagram blocks that fail to render (```array, ```tree, ...),
- ```include blocks whose file doesn't exist,
- internal links (#/design/learn/<page>/<section>, #/algo/learn/..., #/algo/problem/...,
  #/tech/<page>/<section>, #/tech/<page>/files/<path>) whose target doesn't exist,
- algorithm explanations without exactly one empty ```solution block (it marks where solution.py
  is shown),
- design questions whose `foundations` references don't resolve, or whose reference design has
  no Mermaid diagram,
- foundations and tech pages without a summary paragraph or with duplicate section titles,
- tech page sections with the id "files", which is the route of the page's file browser,
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
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from swe_prac import algorithms, config, pages, problems, tech  # noqa: E402

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


def _algo_ids() -> set[str]:
    folder = config.ALGO_DIR if hasattr(config, "ALGO_DIR") else ROOT / "algorithms"
    if not folder.exists():
        return set()
    return {p.name for p in folder.iterdir() if (p / "problem.json").exists()}


def _tech_files() -> dict[str, set[str]]:
    """The files each tech page's file browser lists, by page slug (pages with a project)."""
    out = {}
    for page in pages.list_pages(config.TECH_DIR):
        info = tech.project(page)
        if info is not None:
            out[page.slug] = {f["path"] for f in info["files"]}
    return out


def check_links(html: str, where: str, targets: dict, errors: list[str]) -> None:
    for href in LINK.findall(html):
        m = re.fullmatch(r"#/tech/([\w-]+)/files(?:/(.+))?", href)
        if m:
            slug, path = m.group(1), unquote(m.group(2) or "")
            files = targets["tech_files"].get(slug)
            if slug not in targets["tech"]:
                errors.append(f"{where}: link to unknown page {href}")
            elif files is None:
                errors.append(f"{where}: link to the files of {slug}, which has no project folder")
            elif path and path not in files:
                errors.append(f"{where}: link to unknown file {href}")
            continue
        m = re.fullmatch(r"#/(design|algo)/learn(?:/([\w-]+))?(?:/([\w-]+))?", href)
        m = m or re.fullmatch(r"#/(tech)(?:/([\w-]+))?(?:/([\w-]+))?", href)
        if m:
            track, slug, section = m.groups()
            sections = targets[track]
            if slug and slug not in sections:
                errors.append(f"{where}: link to unknown page {href}")
            elif section and section not in sections[slug]:
                errors.append(f"{where}: link to unknown section {href}")
            continue
        m = re.fullmatch(r"#/algo/problem/([\w-]+)(?:/[\w-]+)?", href)
        if m and m.group(1) not in targets["algo_problems"]:
            errors.append(f"{where}: link to unknown problem {href}")


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
    which = set(argv) or {"designs", "algorithms", "tech"}
    errors: list[str] = []
    design_dir = config.DESIGNS_DIR / "foundations"
    algo_root = getattr(config, "ALGO_DIR", ROOT / "algorithms")
    targets = {
        "design": _sections(design_dir),
        "algo": _sections(algo_root / "foundations"),
        "algo_problems": _algo_ids(),
        "tech": _sections(config.TECH_DIR),
        "tech_files": _tech_files(),
    }
    summary = []
    if "designs" in which:
        n = check_pages(design_dir, "designs/foundations", targets, errors)
        from swe_prac import designs

        for q in designs.list_questions():
            where = f"designs/{q.id}"
            reference = q.path / "reference.md"
            if reference.exists():
                text = reference.read_text(encoding="utf-8")
                check_source(text, f"{where}/reference.md", errors)
                if not MERMAID_BLOCK.search(text):
                    errors.append(f"{where}/reference.md: no design diagram (a ```mermaid block)")
            check_html(designs.reference_html(q), f"{where}/reference.md", targets, errors)
            data = json.loads((q.path / "design.json").read_text(encoding="utf-8"))
            for ref in data.get("foundations", []):
                slug, _, section = ref.partition("/")
                known = targets["design"].get(slug)
                if known is None or (section and section not in known):
                    errors.append(f"{where}/design.json: foundations link {ref!r} doesn't resolve")
        summary.append(f"{n} design foundations pages")
    if "algorithms" in which and (algo_root / "foundations").exists():
        n = check_pages(algo_root / "foundations", "algorithms/foundations", targets, errors)
        summary.append(f"{n} algorithm foundations pages")
        for pid in sorted(targets["algo_problems"]):
            for name in ("statement.md", "hints.md", "explanation.md"):
                path = algo_root / pid / name
                if path.exists():
                    text = path.read_text(encoding="utf-8")
                    where = f"algorithms/{pid}/{name}"
                    check_source(text, where, errors)
                    if name == "explanation.md":
                        if len(algorithms.SOLUTION_MARKER.findall(text)) != 1:
                            errors.append(f"{where}: needs one empty ```solution block")
                        solution = (algo_root / pid / "solution.py").read_text(encoding="utf-8")
                        text = algorithms.expand_solution(text, solution)
                    check_html(problems.render_markdown(text), where, targets, errors)
        summary.append(f"{len(targets['algo_problems'])} algorithm problems")
    if "tech" in which:
        n = check_pages(config.TECH_DIR, "tech", targets, errors)
        for slug, ids in sorted(targets["tech"].items()):
            if "files" in ids:
                errors.append(
                    f"tech page {slug}: a section can't have the id 'files'"
                    f" (#/tech/{slug}/files is its file browser); rename the heading"
                )
        summary.append(f"{n} tech pages")
    for e in errors:
        print("ERROR", e)
    print(("FAILED: " if errors else "OK: ") + ", ".join(summary) + f" ({len(errors)} problems)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
