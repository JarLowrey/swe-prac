"""Shared test scaffolding: temp dirs, the fixture problem set, a fake clock, an API client."""

from __future__ import annotations

import shutil
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest import mock

# Must run before fastapi.testclient is imported, which is what emits the warning.
warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`")

from fastapi.testclient import TestClient  # noqa: E402

from swe_prac import config, problems, sessions  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"

COUNTER_FULL = """
class Counter:
    def __init__(self):
        self.counts = {}

    def incr(self, timestamp, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def get(self, timestamp, key):
        return self.counts.get(key)

    def reset(self, timestamp, key):
        if key not in self.counts:
            return False
        self.counts[key] = 0
        return True

    def total(self, timestamp):
        return sum(self.counts.values())
"""


class FakeClock:
    def __init__(self, start: float = 1_000_000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TempDirCase(unittest.TestCase):
    """Gives each test a private `self.tmp_path`."""

    def setUp(self) -> None:
        super().setUp()
        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        self.tmp_path = Path(tmp.name)

    def patch(self, target, name: str, value) -> None:
        self.enterContext(mock.patch.object(target, name, value))


class EnvCase(TempDirCase):
    """Isolated data dir, the fixture problem set and a fake clock (`self.clock`)."""

    def setUp(self) -> None:
        super().setUp()
        problems_dir = self.tmp_path / "problems"
        shutil.copytree(FIXTURES / "problems", problems_dir)
        self.patch(config, "PROBLEMS_DIR", problems_dir)
        self.patch(config, "REFERENCE_DIR", self.tmp_path / "reference")
        self.patch(config, "DATA_DIR", self.tmp_path / "data")
        problems.conventions_html.cache_clear()
        self.clock = FakeClock()
        self.patch(sessions, "clock", self.clock)


class ClientCase(EnvCase):
    """EnvCase plus an HTTP client for the app (`self.client`)."""

    def setUp(self) -> None:
        super().setUp()
        from swe_prac.app import app

        self.client = self.enterContext(TestClient(app))


class RealClientCase(TempDirCase):
    """The real problem set in problems/, with isolated history and a fake clock."""

    def setUp(self) -> None:
        super().setUp()
        self.patch(config, "DATA_DIR", self.tmp_path / "data")
        self.clock = FakeClock()
        self.patch(sessions, "clock", self.clock)
        from swe_prac.app import app

        self.client = self.enterContext(TestClient(app))
