"""job-apply's batch driver (apply.py) runs any headless AI agent: the command comes from
$JOB_SEARCH_AGENT, and the step's answer is the last JSON object with the right keys in the
agent's output, however the agent wraps it."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "jobs" / "job-search" / "skills" / "job-apply" / "scripts" / "apply.py"
spec = importlib.util.spec_from_file_location("apply_driver", SCRIPT)
A = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = A  # @dataclass looks its module up here
spec.loader.exec_module(A)

KEYS = ["people", "summary"]


class LastJson(unittest.TestCase):
    def test_answer_at_the_end_of_free_text(self):
        out = 'Found three people.\n{"people": 3, "summary": "a recruiter, an engineer, a manager"}\n'
        self.assertEqual(A.last_json(out, KEYS), {"people": 3, "summary": "a recruiter, an engineer, a manager"})

    def test_last_matching_object_wins_and_others_are_ignored(self):
        out = '{"people": 1, "summary": "draft"} then {"note": "x"} and {"people": 2, "summary": "final"}'
        self.assertEqual(A.last_json(out, KEYS)["summary"], "final")

    def test_answer_inside_a_wrapper(self):
        wrapped = json.dumps({"type": "result", "result": 'Done.\n```json\n{"people": 2, "summary": "ok"}\n```'})
        self.assertEqual(A.last_json(wrapped, KEYS), {"people": 2, "summary": "ok"})
        nested = json.dumps({"output": {"answer": {"people": 4, "summary": "nested"}}})
        self.assertEqual(A.last_json(nested, KEYS)["people"], 4)

    def test_no_answer(self):
        self.assertIsNone(A.last_json("I couldn't finish: sign-in page.", KEYS))
        self.assertIsNone(A.last_json('{"people": 2}', KEYS))
        self.assertIsNone(A.last_json("{not json", KEYS))


class AgentCommand(unittest.TestCase):
    def test_unset_says_how_to_set_it(self):
        with mock.patch.dict(os.environ, {}, clear=True), self.assertRaises(SystemExit) as cm:
            A.agent_command("hi")
        self.assertIn("JOB_SEARCH_AGENT", str(cm.exception))

    def test_prompt_goes_on_stdin_or_in_place_of_the_placeholder(self):
        with mock.patch.dict(os.environ, {"JOB_SEARCH_AGENT": '["my-agent-x", "--headless"]'}):
            self.assertEqual(A.agent_command("hi"), (["my-agent-x", "--headless"], "hi"))
        with mock.patch.dict(os.environ, {"JOB_SEARCH_AGENT": 'my-agent-x --ask "{prompt}"'}):
            self.assertEqual(A.agent_command("hi there"), (["my-agent-x", "--ask", "hi there"], None))

    def test_a_bad_setting_is_refused(self):
        for bad in ('["my-agent", 3]', "[]", '["unclosed'):
            with mock.patch.dict(os.environ, {"JOB_SEARCH_AGENT": bad}), self.assertRaises(SystemExit):
                A.agent_command("hi")


class RunAgent(unittest.TestCase):
    """A stand-in agent: a Python script that reads the prompt and prints an answer."""

    def run_stub(self, body: str):
        with tempfile.TemporaryDirectory() as d:
            stub = Path(d) / "agent.py"
            stub.write_text(body, encoding="utf-8")
            (Path(d) / "reference").mkdir()
            env = {"JOB_SEARCH_AGENT": json.dumps([sys.executable, str(stub)]), "JOB_SEARCH_DIR": d}
            with mock.patch.dict(os.environ, env):
                return A.run_agent(A.App(url="https://jobs.example.com/1"), "contacts", "Find people.",
                                   SimpleNamespace(timeout=1))

    def test_the_prompt_asks_for_the_schema_and_the_answer_is_read(self):
        out, error = self.run_stub(
            "import sys, json\n"
            "prompt = sys.stdin.read()\n"
            "assert 'JSON Schema' in prompt and '\"people\"' in prompt, prompt\n"
            "print('working...')\n"
            "print(json.dumps({'people': 3, 'summary': 'three people'}))\n")
        self.assertEqual((out, error), ({"people": 3, "summary": "three people"}, ""))

    def test_a_failed_agent_reports_why(self):
        out, error = self.run_stub("import sys\nprint('blocked by a sign-in page')\nsys.exit(2)\n")
        self.assertIsNone(out)
        self.assertIn("agent exited 2", error)
        self.assertIn("blocked by a sign-in page", error)


if __name__ == "__main__":
    unittest.main()
