"""Checks over the real system design set in designs/ (not the fixture)."""

from __future__ import annotations

import re
import unittest

from swe_prac import designs

REAL = designs.list_questions()


class DesignCatalogueTests(unittest.TestCase):
    def test_all_ten_questions_load_in_order(self):
        self.assertEqual([q.number for q in REAL], list(range(1, 11)))
        for q in REAL:
            self.assertEqual(q.path.name, q.id)

    def test_every_question_is_complete(self):
        for q in REAL:
            with self.subTest(question=q.id):
                self.assertTrue(q.prompt.startswith("Design "))
                self.assertTrue(q.hard_part)
                self.assertTrue(q.building_blocks)
                self.assertGreaterEqual(len(q.key_points), 4)
                self.assertTrue(designs.reference_html(q))

    def test_every_reference_follows_readddd(self):
        # Each framework step opens a paragraph with its bold label, in order: Requirements,
        # Estimates, API, Data model, Diagram, Deep dives, Done. Other bold labels may sit between.
        titles = [s["title"] for s in designs.steps()]
        self.assertEqual("".join(t[0] for t in titles), "READDDD")
        for q in REAL:
            with self.subTest(question=q.id):
                labels = re.findall(r"^\*\*([^*]+?)\.\*\*", designs.reference_markdown(q), re.M)
                self.assertEqual([t for t in labels if t in titles], titles)

    def test_framework_has_the_checklist_guides_and_step_titles(self):
        # The titles only label old sessions' per-step notes on their review.
        steps = designs.steps()
        self.assertEqual([s["step"] for s in steps], list(range(1, 8)))
        for s in steps:
            self.assertEqual(sorted(s), ["step", "title"])
            self.assertTrue(s["title"])
        self.assertEqual(len(designs.checklist()), 10)
        self.assertIn("What the interviewer is grading", designs.guide_html("framework"))
        self.assertTrue(designs.guide_html("walkthrough"))


if __name__ == "__main__":
    unittest.main()
