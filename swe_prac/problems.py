"""Loading problem packages from problems/<pid>/ (built by tools/build_problem.py)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import markdown as md

from . import config


class ProblemNotFound(KeyError):
    pass


@dataclass(frozen=True)
class Problem:
    id: str
    number: int
    title: str
    summary: str
    class_name: str
    levels: tuple[dict, ...]  # {"level", "title", "methods"}
    path: Path

    def level_title(self, level: int) -> str:
        return next(lv["title"] for lv in self.levels if lv["level"] == level)

    def public(self) -> dict:
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "summary": self.summary,
            "class_name": self.class_name,
            "levels": [{"level": lv["level"], "title": lv["title"]} for lv in self.levels],
        }


def render_markdown(text: str) -> str:
    return md.markdown(text, extensions=["fenced_code", "tables", "sane_lists"])


def _is_ready(path: Path) -> bool:
    return (
        (path / "problem.json").exists()
        and (path / "tests.json").exists()
        and (path / "stubs.json").exists()
    )


def list_problems() -> list[Problem]:
    out = []
    if not config.PROBLEMS_DIR.exists():
        return out
    for path in sorted(config.PROBLEMS_DIR.iterdir()):
        if path.is_dir() and _is_ready(path):
            out.append(_load(path))
    return sorted(out, key=lambda p: p.number)


def get(problem_id: str) -> Problem:
    path = config.PROBLEMS_DIR / problem_id
    if "/" in problem_id or "\\" in problem_id or not _is_ready(path):
        raise ProblemNotFound(problem_id)
    return _load(path)


def _load(path: Path) -> Problem:
    data = json.loads((path / "problem.json").read_text(encoding="utf-8"))
    return Problem(
        id=data["id"],
        number=data["number"],
        title=data["title"],
        summary=data["summary"],
        class_name=data["class_name"],
        levels=tuple(data["levels"]),
        path=path,
    )


def statement_html(problem: Problem, level: int) -> str:
    text = (problem.path / "statement" / f"level{level}.md").read_text(encoding="utf-8")
    return render_markdown(text)


def review_html(problem: Problem, name: str) -> str:
    return render_markdown((problem.path / "review" / f"{name}.md").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def conventions_html() -> str:
    return render_markdown((config.PROBLEMS_DIR / "conventions.md").read_text(encoding="utf-8"))


def stubs(problem: Problem) -> dict[str, str]:
    return json.loads((problem.path / "stubs.json").read_text(encoding="utf-8"))


def starter_code(problem: Problem) -> str:
    s = stubs(problem)
    return f"class {problem.class_name}:\n{s['init']}\n{s['1']}"


def level_stubs(problem: Problem, level: int) -> str:
    return stubs(problem)[str(level)]


def tests(problem: Problem, max_level: int, include_hidden: bool) -> list[dict]:
    data = json.loads((problem.path / "tests.json").read_text(encoding="utf-8"))["tests"]
    return [
        t
        for t in data
        if t["level"] <= max_level and (include_hidden or t["visibility"] == "shown")
    ]


def reference_code(problem: Problem) -> str | None:
    path = config.REFERENCE_DIR / problem.id / "solution.py"
    return path.read_text(encoding="utf-8") if path.exists() else None
