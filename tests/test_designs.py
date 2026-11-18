"""Checks over the real system design set in designs/ (not the fixture)."""

from __future__ import annotations

import unittest

from support import RealClientCase

from swe_prac import config, designs

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
                html = designs.reference_html(q)
                for section in ("Requirements.", "Estimates.", "Deep dives."):
                    self.assertIn(section, html)

    def test_framework_steps_fill_the_time_limit(self):
        steps = designs.steps()
        self.assertEqual([s["step"] for s in steps], list(range(1, 8)))
        self.assertEqual(sum(s["minutes"] for s in steps) * 60, config.DESIGN_TIME_LIMIT_SECONDS)
        for s in steps:
            self.assertTrue(s["title"] and s["short"] and s["output"] and s["guide"])
        self.assertEqual(len(designs.checklist()), 10)
        self.assertIn("What the interviewer is grading", designs.guide_html("framework"))
        self.assertTrue(designs.guide_html("walkthrough"))


class RealDesignSessionTests(RealClientCase):
    def test_a_session_on_a_real_question_round_trips(self):
        listed = self.client.get("/api/design/questions").json()["questions"]
        self.assertEqual(len(listed), 10)
        s = self.client.post(
            "/api/design/sessions", json={"question_id": REAL[0].id, "mode": "strict"}
        ).json()
        self.assertEqual(len(s["steps"]), 7)
        self.client.post(f"/api/design/sessions/{s['id']}/end")
        review = self.client.get(f"/api/design/sessions/{s['id']}/review").json()
        self.assertEqual(len(review["results"]["steps"]), 7)
        self.assertEqual(len(review["checklist"]), 10)


if __name__ == "__main__":
    unittest.main()
