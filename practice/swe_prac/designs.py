"""System design questions from designs/<qid>/ and the shared 45-minute framework.

Each question is designs/<qid>/design.json (prompt, hints, key points) plus reference.md (the
worked design). designs/framework.json holds the self-review checklist and the seven step
titles, which only label the per-step notes of sessions saved before the whiteboard (the round
itself isn't split into steps); framework.md and walkthrough.md are the guide page.
designs/foundations/ holds the study pages (see pages.py); a question's hints link to the
sections it relies on.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import config, pages
from .problems import render_markdown


class QuestionNotFound(KeyError):
    pass


@dataclass(frozen=True)
class Question:
    id: str
    number: int
    title: str
    prompt: str
    hard_part: str
    building_blocks: tuple[str, ...]
    key_points: tuple[str, ...]
    path: Path
    foundations: tuple[str, ...] = ()  # "page-slug/section-id" references into foundations/

    def public(self) -> dict:
        """What anyone may see, including during a session: the prompt, nothing that hints."""
        return {"id": self.id, "number": self.number, "title": self.title, "prompt": self.prompt}

    def hints(self) -> dict:
        return {
            "hard_part": self.hard_part,
            "building_blocks": list(self.building_blocks),
            "foundations": foundation_links(self.foundations),
        }


def _is_ready(path: Path) -> bool:
    return (path / "design.json").exists() and (path / "reference.md").exists()


def _load(path: Path) -> Question:
    data = json.loads((path / "design.json").read_text(encoding="utf-8"))
    return Question(
        id=data["id"],
        number=data["number"],
        title=data["title"],
        prompt=data["prompt"],
        hard_part=data["hard_part"],
        building_blocks=tuple(data["building_blocks"]),
        key_points=tuple(data["key_points"]),
        path=path,
        foundations=tuple(data.get("foundations", ())),
    )


def list_questions() -> list[Question]:
    if not config.DESIGNS_DIR.exists():
        return []
    found = [_load(p) for p in config.DESIGNS_DIR.iterdir() if p.is_dir() and _is_ready(p)]
    return sorted(found, key=lambda q: q.number)


def get(question_id: str) -> Question:
    path = config.DESIGNS_DIR / question_id
    if "/" in question_id or "\\" in question_id or not _is_ready(path):
        raise QuestionNotFound(question_id)
    return _load(path)


def reference_markdown(question: Question) -> str:
    return (question.path / "reference.md").read_text(encoding="utf-8")


def reference_html(question: Question) -> str:
    return render_markdown(reference_markdown(question))


def framework() -> dict:
    """{"steps": [{step, title}], "checklist": [...]} from designs/framework.json."""
    return json.loads((config.DESIGNS_DIR / "framework.json").read_text(encoding="utf-8"))


def steps() -> list[dict]:
    return framework()["steps"]


def checklist() -> list[str]:
    return framework()["checklist"]


def guide_html(name: str) -> str:
    """framework.md or walkthrough.md rendered; empty if the file is missing."""
    path = config.DESIGNS_DIR / f"{name}.md"
    return render_markdown(path.read_text(encoding="utf-8")) if path.exists() else ""


# -- foundations (study pages) -----------------------------------------------------------
def foundations_dir() -> Path:
    return config.DESIGNS_DIR / "foundations"


def foundation_links(refs) -> list[dict]:
    """Resolve "page/section" references to titled links (see pages.links)."""
    return pages.links(foundations_dir(), "#/design/learn", refs)
