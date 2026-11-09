from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from swe_prac import config, sessions

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


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Isolated data dir + fixture problem set."""
    problems_dir = tmp_path / "problems"
    shutil.copytree(FIXTURES / "problems", problems_dir)
    monkeypatch.setattr(config, "PROBLEMS_DIR", problems_dir)
    monkeypatch.setattr(config, "REFERENCE_DIR", tmp_path / "reference")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    from swe_prac import problems

    problems.conventions_html.cache_clear()
    return tmp_path


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(sessions, "clock", fake)
    return fake


@pytest.fixture
def client(env, clock):
    from swe_prac.app import app

    with TestClient(app) as c:
        yield c
