from __future__ import annotations

import unittest

from support import EnvCase

from swe_prac import db, sessions
from swe_prac.sessions import SessionError


class SessionTests(EnvCase):
    def setUp(self):
        super().setUp()
        db.init()
        self.conn = self.enterContext(db.connect())

    def _new(self, mode="pausable"):
        return sessions.get(self.conn, sessions.create(self.conn, "p0_counter", mode, "code"))

    def _row(self, session_id):
        return sessions.get(self.conn, session_id)

    def test_elapsed_excludes_pauses(self):
        row = self._new()
        self.clock.advance(100)
        sessions.pause(self.conn, row)
        self.clock.advance(1000)  # paused time doesn't count
        row = self._row(row["id"])
        self.assertAlmostEqual(sessions.elapsed(row), 100)
        sessions.resume(self.conn, row)
        self.clock.advance(50)
        row = self._row(row["id"])
        self.assertAlmostEqual(sessions.elapsed(row), 150)
        self.assertIsNotNone(sessions.pauses(self.conn, row["id"])[0]["ended_at"])

    def test_strict_cannot_pause_and_one_active_session(self):
        row = self._new("strict")
        with self.assertRaisesRegex(SessionError, "strict"):
            sessions.pause(self.conn, row)
        with self.assertRaisesRegex(SessionError, "active session"):
            sessions.create(self.conn, "p0_counter", "pausable", "code")

    def test_cannot_pause_in_overtime_or_edit_while_paused(self):
        row = self._new()
        sessions.pause(self.conn, row)
        with self.assertRaisesRegex(SessionError, "paused"):
            sessions.save_code(self.conn, self._row(row["id"]), "x", None)
        sessions.resume(self.conn, self._row(row["id"]))
        self.clock.advance(90 * 60 + 1)
        with self.assertRaisesRegex(SessionError, "Time is up"):
            sessions.pause(self.conn, self._row(row["id"]))

    def test_results_split_timed_and_overtime(self):
        row = self._new("strict")
        sid = row["id"]
        self.clock.advance(10 * 60)
        sessions.complete_level(self.conn, self._row(sid))  # L1 at 10:00
        self.clock.advance(70 * 60)
        sessions.complete_level(self.conn, self._row(sid))  # L2 at 80:00
        sessions.record_submission(
            self.conn,
            self._row(sid),
            "submit",
            3,
            False,
            {"3": {"shown_passed": 2, "shown_total": 3, "hidden_passed": 5, "hidden_total": 9}},
            0,
        )
        self.clock.advance(20 * 60)
        sessions.complete_level(self.conn, self._row(sid))  # L3 at 100:00 (overtime)
        sessions.finish(self.conn, self._row(sid))
        res = sessions.results(self.conn, self._row(sid))
        self.assertEqual(res["timed"]["levels_completed"], 2)
        self.assertEqual(res["timed"]["stopped_level"], 3)
        self.assertEqual(res["timed"]["stopped_level_ratio"]["passed"], 7)
        self.assertEqual(res["timed"]["stopped_level_ratio"]["total"], 12)
        self.assertEqual(res["final"]["levels_completed"], 3)
        self.assertIs(res["levels"][2]["overtime"], True)
        self.assertAlmostEqual(res["levels"][1]["split"], 70 * 60)
        self.assertAlmostEqual(res["overtime_seconds"], 10 * 60)

    def test_finish_while_paused_closes_pause(self):
        row = self._new()
        self.clock.advance(30)
        sessions.pause(self.conn, row)
        self.clock.advance(500)
        sessions.finish(self.conn, self._row(row["id"]))
        row = self._row(row["id"])
        self.assertEqual(row["status"], "finished")
        self.assertAlmostEqual(sessions.elapsed(row), 30)


if __name__ == "__main__":
    unittest.main()
