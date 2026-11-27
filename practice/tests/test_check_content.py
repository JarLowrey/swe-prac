"""tools/check_content.py: the Mermaid list-label check, and the content checks over the
fixtures and over the real study content."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

from support import EnvCase

from swe_prac import algorithms, config

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import check_content  # noqa: E402


def mermaid_errors(body: str) -> list[str]:
    errors: list[str] = []
    check_content.check_mermaid(f"```mermaid\n{body}\n```\n", "page", errors)
    return errors


def run_main(*argv: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = check_content.main(list(argv))
    return code, out.getvalue()


class MermaidLabelTests(unittest.TestCase):
    def test_labels_that_start_like_a_list_are_flagged(self):
        lines = [
            'A["1. read"]',
            'A["2) write"]',
            "A[3. step]",
            'A --> B["- item"]',
            "A -->|1. first| B",
            "A{{* star}}",
            'subgraph "1. Setup"',
        ]
        for line in lines:
            with self.subTest(line=line):
                self.assertEqual(len(mermaid_errors(f"flowchart LR\n  {line}")), 1)
        self.assertEqual(len(mermaid_errors("stateDiagram-v2\n  A --> B: 1. retry")), 1)

    def test_other_labels_are_fine(self):
        fine = [
            'flowchart LR\n  A["(1) read"] --> B["Step 2: write"]',
            'flowchart LR\n  A["ways(1) = 1"] --> B["sum<br/>- item"]',
            'flowchart TD\n  A["2024 plan"]',
            "sequenceDiagram\n  A->>B: 1. request",  # sequence diagrams are not affected
        ]
        for body in fine:
            with self.subTest(body=body):
                self.assertEqual(mermaid_errors(body), [])


class CaptionTests(unittest.TestCase):
    def test_long_captions_are_flagged(self):
        errors: list[str] = []
        long_caption = "x" * 101
        frames = [f"values: 1\ncaption: {'y' * 100}", f"values: 2\ncaption: {long_caption}"]
        text = "```array\n" + "\n---\n".join(frames) + "\n```\n"
        check_content.check_captions(text, "page", errors)
        self.assertEqual(len(errors), 1)
        self.assertIn("101 characters", errors[0])
        # Only data-structure blocks have captions.
        check_content.check_captions(f"```python\ncaption: {long_caption}\n```\n", "page", errors)
        self.assertEqual(len(errors), 1)


class FixtureContentTests(EnvCase):
    def test_the_fixture_content_passes(self):
        code, out = run_main()
        self.assertEqual(code, 0, out)
        self.assertIn("1 algorithm foundations pages, 2 algorithm problems", out)
        self.assertIn("1 tech pages", out)

    def test_broken_tech_includes_and_links_are_reported(self):
        page = config.TECH_DIR / "01_demo.md"
        page.write_text(
            "# Demo\n\nSummary.\n\n## Code\n\n```include\ndemo/gone.ts\n```\n\n"
            "See [this](#/tech/demo/nope) and [that](#/tech/missing).\n",
            encoding="utf-8",
        )
        code, out = run_main("tech")
        self.assertEqual(code, 1)
        self.assertIn("Include error: no file demo/gone.ts", out)
        self.assertIn("link to unknown section #/tech/demo/nope", out)
        self.assertIn("link to unknown page #/tech/missing", out)

    def test_links_into_the_file_browser_are_checked(self):
        page = config.TECH_DIR / "01_demo.md"
        page.write_text(
            "# Demo\n\nSummary.\n\n## Code\n\n"
            "[ok](#/tech/demo/files) [ok](#/tech/demo/files/hello.ts)"
            " [bad](#/tech/demo/files/gone.ts) [bad](#/tech/missing/files/x.ts)\n",
            encoding="utf-8",
        )
        code, out = run_main("tech")
        self.assertEqual(code, 1)
        self.assertIn("link to unknown file #/tech/demo/files/gone.ts", out)
        self.assertIn("link to unknown page #/tech/missing/files/x.ts", out)
        self.assertEqual(out.count("ERROR"), 2, out)  # the two good links pass

    def test_a_tech_section_cannot_take_the_file_browser_route(self):
        page = config.TECH_DIR / "01_demo.md"
        page.write_text("# Demo\n\nSummary.\n\n## Files\n\nText.\n", encoding="utf-8")
        code, out = run_main("tech")
        self.assertEqual(code, 1)
        self.assertIn("tech page demo: a section can't have the id 'files'", out)

    def test_broken_links_diagrams_and_labels_are_reported(self):
        explanation = config.ALGO_DIR / "x01_pair_sum" / "explanation.md"
        explanation.write_text(
            "See [this](#/algo/learn/basics/nope) and [that](#/algo/problem/x99_missing).\n\n"
            "```array\npointers: i=0\n```\n\n"
            '```mermaid\nflowchart LR\n  A["1. scan"] --> B\n```\n',
            encoding="utf-8",
        )
        code, out = run_main("algorithms")
        self.assertEqual(code, 1)
        self.assertIn("link to unknown section #/algo/learn/basics/nope", out)
        self.assertIn("link to unknown problem #/algo/problem/x99_missing", out)
        self.assertIn("array needs", out)
        self.assertIn("Unsupported markdown: list", out)

    def test_the_solution_marker_expands_to_solution_py(self):
        solution = (config.ALGO_DIR / "x01_pair_sum" / "solution.py").read_text(encoding="utf-8")
        text = "## The solution\n\n```solution\n```\n\nAfter.\n"
        out = algorithms.expand_solution(text, solution)
        self.assertIn("```python\nclass Solution:", out)
        self.assertIn("return [seen[target - x], i]", out)
        self.assertNotIn("```solution", out)
        self.assertTrue(out.endswith("```\n\nAfter.\n"))

    def test_an_explanation_needs_exactly_one_solution_marker(self):
        explanation = config.ALGO_DIR / "x01_pair_sum" / "explanation.md"
        text = explanation.read_text(encoding="utf-8")
        marker = "```solution\n```"
        for broken in (text.replace(marker, "```python\npass\n```"), text + "\n" + marker + "\n"):
            explanation.write_text(broken, encoding="utf-8")
            code, out = run_main("algorithms")
            self.assertEqual(code, 1)
            self.assertIn("x01_pair_sum/explanation.md: needs one empty ```solution block", out)

    def test_design_foundations_references_must_resolve(self):
        path = config.DESIGNS_DIR / "d00_pastebin" / "design.json"
        meta = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps({**meta, "foundations": ["networking/nope"]}), encoding="utf-8")
        code, out = run_main("designs")
        self.assertEqual(code, 1)
        self.assertIn("foundations link 'networking/nope' doesn't resolve", out)

    def test_a_reference_design_needs_a_diagram(self):
        path = config.DESIGNS_DIR / "d00_pastebin" / "reference.md"
        path.write_text("**Requirements.** Create and read pastes.\n", encoding="utf-8")
        code, out = run_main("designs")
        self.assertEqual(code, 1)
        self.assertIn("d00_pastebin/reference.md: no design diagram", out)


class RealContentTests(unittest.TestCase):
    def test_the_real_study_content_passes(self):
        code, out = run_main()
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
