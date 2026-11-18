"""System design sessions over HTTP, against the fixture question set (3 steps: 15/20/10 min)."""

from __future__ import annotations

import unittest

from support import ClientCase

QID = "d00_pastebin"


class DesignApiTests(ClientCase):
    def _start(self, mode="pausable", question_id=QID):
        res = self.client.post(
            "/api/design/sessions", json={"question_id": question_id, "mode": mode}
        )
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()

    def _post(self, sid, action, **body):
        return self.client.post(f"/api/design/sessions/{sid}/{action}", json=body)

    def _notes(self, sid, **body):
        return self.client.put(f"/api/design/sessions/{sid}/notes", json=body)

    def _end(self, sid):
        res = self._post(sid, "end")
        self.assertEqual(res.status_code, 200, res.text)

    def test_start_gives_the_prompt_steps_and_starter_notes_but_no_answers(self):
        s = self._start()
        self.assertEqual(
            s["question"]["prompt"], "Design a service for sharing text snippets by link."
        )
        self.assertEqual(s["current_step"], 1)
        self.assertEqual([st["step"] for st in s["steps"]], [1, 2, 3])
        self.assertEqual(s["step_starts"], {"1": 0})
        self.assertEqual(s["notes"]["1"], "Functional:\n- \n")
        self.assertEqual(s["timer"]["limit"], 45 * 60)
        text = str(s)
        for spoiler in ("Read-heavy traffic", "Cached hot pastes", "Deep dives"):
            self.assertNotIn(spoiler, text)

    def test_notes_merge_and_the_diagram_is_kept(self):
        sid = self._start()["id"]
        self.assertEqual(self._notes(sid, notes={"2": "boxes", "99": "ignored"}).status_code, 200)
        diagram = {"nodes": [{"id": "n1", "x": 10, "y": 20, "label": "API"}], "edges": []}
        self._notes(sid, diagram=diagram)
        s = self.client.get(f"/api/design/sessions/{sid}").json()
        self.assertEqual(s["notes"]["1"], "Functional:\n- \n")  # untouched step keeps its text
        self.assertEqual(s["notes"]["2"], "boxes")
        self.assertNotIn("99", s["notes"])
        self.assertEqual(s["diagram"], diagram)

    def test_steps_only_move_forward_and_record_when_they_started(self):
        sid = self._start()["id"]
        self.clock.advance(300)
        s = self._post(sid, "step", step=2).json()
        self.assertEqual(s["current_step"], 2)
        self.assertEqual(s["step_starts"], {"1": 0, "2": 300})
        self.assertEqual(self._post(sid, "step", step=1).status_code, 400)
        self.assertEqual(self._post(sid, "step", step=2).status_code, 400)
        self.assertEqual(self._post(sid, "step", step=4).status_code, 400)

    def test_skipping_a_step_is_allowed(self):
        sid = self._start()["id"]
        self.clock.advance(60)
        self.assertEqual(self._post(sid, "step", step=3).json()["current_step"], 3)

    def test_pause_blocks_work_and_strict_cannot_pause(self):
        sid = self._start()["id"]
        self.clock.advance(100)
        self.assertEqual(self._post(sid, "pause").status_code, 200)
        self.clock.advance(1000)
        self.assertEqual(self._notes(sid, notes={"1": "x"}).status_code, 409)
        self.assertEqual(self._post(sid, "step", step=2).status_code, 409)
        timer = self._post(sid, "resume").json()
        self.assertAlmostEqual(timer["elapsed"], 100)  # paused time doesn't count
        self._end(sid)

        strict = self._start(mode="strict")["id"]
        self.assertEqual(self._post(strict, "pause").status_code, 409)

    def test_one_active_design_session_but_coding_can_run_alongside(self):
        self._start()
        res = self.client.post("/api/design/sessions", json={"question_id": QID, "mode": "strict"})
        self.assertEqual(res.status_code, 409)
        coding = self.client.post(
            "/api/sessions", json={"problem_id": "p0_counter", "mode": "strict"}
        )
        self.assertEqual(coding.status_code, 200, coding.text)
        self.assertIsNotNone(self.client.get("/api/design/active").json()["session"])
        self.assertIsNotNone(self.client.get("/api/active").json()["session"])

    def test_review_opens_only_after_the_session_ends(self):
        sid = self._start()["id"]
        self.assertEqual(self.client.get(f"/api/design/sessions/{sid}/review").status_code, 409)
        self._end(sid)
        self.assertEqual(self.client.get(f"/api/design/sessions/{sid}").status_code, 410)
        review = self.client.get(f"/api/design/sessions/{sid}/review").json()
        self.assertIn("Cache hot pastes", review["reference_html"])
        self.assertEqual(
            review["key_points"], ["Stored blobs in object storage", "Cached hot pastes"]
        )
        self.assertEqual(review["checklist"][0], "Asked about scale.")
        self.assertEqual(review["hints"]["hard_part"], "Read-heavy traffic")
        self.assertIsNone(review["assessment"])
        self.assertIsNone(review["score"])

    def test_end_saves_the_final_notes(self):
        sid = self._start()["id"]
        self._post(sid, "end", notes={"3": "last words"}, diagram={"nodes": [], "edges": []})
        review = self.client.get(f"/api/design/sessions/{sid}/review").json()
        self.assertEqual(review["notes"]["3"], "last words")

    def test_pacing_per_step(self):
        sid = self._start()["id"]
        self.clock.advance(20 * 60)  # requirements: 20 min against a 15 min target
        self._post(sid, "step", step=3)  # skips step 2
        self.clock.advance(5 * 60)
        self._end(sid)
        res = self.client.get(f"/api/design/sessions/{sid}/review").json()["results"]
        req, design, wrap = res["steps"]
        self.assertEqual((req["started_at"], req["spent"], req["delta"]), (0, 1200, 300))
        self.assertIsNone(design["started_at"])
        self.assertIsNone(design["spent"])
        self.assertEqual(design["target_start"], 15 * 60)
        self.assertEqual((wrap["started_at"], wrap["spent"]), (1200, 300))
        self.assertEqual(res["steps_reached"], 2)
        self.assertEqual(res["elapsed"], 1500)
        self.assertEqual(res["overtime_seconds"], 0)

    def test_overtime_step_is_flagged(self):
        sid = self._start(mode="strict")["id"]
        self.clock.advance(50 * 60)
        self._post(sid, "step", step=2)
        self._end(sid)
        res = self.client.get(f"/api/design/sessions/{sid}/review").json()["results"]
        self.assertTrue(res["steps"][1]["overtime"])
        self.assertFalse(res["steps"][0]["overtime"])
        self.assertEqual(res["overtime_seconds"], 5 * 60)

    def test_self_review_scores_the_session(self):
        sid = self._start()["id"]
        url = f"/api/design/sessions/{sid}/assessment"
        # Still running: no self-review yet.
        self.assertEqual(self.client.put(url, json={"checklist": [0]}).status_code, 409)
        self._end(sid)
        self.assertEqual(self.client.put(url, json={"checklist": [3]}).status_code, 400)
        self.assertEqual(self.client.put(url, json={"key_points": [-1]}).status_code, 400)
        res = self.client.put(url, json={"checklist": [2, 0, 0], "key_points": [1]}).json()
        self.assertEqual(res["assessment"], {"checklist": [0, 2], "key_points": [1]})
        self.assertEqual(res["score"], {"done": 3, "total": 5, "checklist": 2, "key_points": 1})

        review = self.client.get(f"/api/design/sessions/{sid}/review").json()
        self.assertEqual(review["score"]["done"], 3)
        (listed,) = self.client.get("/api/design/questions").json()["questions"]
        self.assertEqual((listed["attempts"], listed["best"]["done"]), (1, 3))
        (row,) = self.client.get("/api/design/history").json()["sessions"]
        self.assertEqual(
            (row["question_title"], row["score"]["done"]), ("Pastebin (test fixture)", 3)
        )

    def test_study_views_are_shut_while_that_question_is_running(self):
        hints = self.client.get(f"/api/design/questions/{QID}/hints").json()
        self.assertEqual(hints["hints"]["building_blocks"], ["object storage", "caching"])
        self.assertNotIn("reference_html", hints)
        ref = self.client.get(f"/api/design/questions/{QID}/reference").json()
        self.assertIn("Cache hot pastes", ref["reference_html"])
        self.assertEqual(self.client.get(f"/api/design/questions/{QID}/bogus").status_code, 404)
        self.assertEqual(self.client.get("/api/design/questions/nope/hints").status_code, 404)

        sid = self._start()["id"]
        self.assertEqual(self.client.get(f"/api/design/questions/{QID}/reference").status_code, 409)
        self._end(sid)
        self.assertEqual(self.client.get(f"/api/design/questions/{QID}/reference").status_code, 200)

    def test_random_start_and_framework(self):
        res = self.client.post("/api/design/sessions", json={"mode": "strict"})
        self.assertEqual(res.json()["question"]["id"], QID)  # the only question
        fw = self.client.get("/api/design/framework").json()
        self.assertEqual(len(fw["checklist"]), 3)
        self.assertIn("test fixture", fw["guide_html"])
        self.assertEqual(fw["walkthrough_html"], "")  # the fixture has no walkthrough.md


if __name__ == "__main__":
    unittest.main()
