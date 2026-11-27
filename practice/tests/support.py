"""Shared test scaffolding: temp dirs and the fixture content set."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from swe_prac import config, problems

FIXTURES = Path(__file__).parent / "fixtures"


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
    """The fixture problem, design, algorithm and tech sets, copied to a temp dir."""

    def setUp(self) -> None:
        super().setUp()
        problems_dir = self.tmp_path / "problems"
        shutil.copytree(FIXTURES / "problems", problems_dir)
        self.patch(config, "PROBLEMS_DIR", problems_dir)
        designs_dir = self.tmp_path / "designs"
        shutil.copytree(FIXTURES / "designs", designs_dir)
        self.patch(config, "DESIGNS_DIR", designs_dir)
        algo_dir = self.tmp_path / "algorithms"
        shutil.copytree(
            FIXTURES / "algorithms", algo_dir, ignore=shutil.ignore_patterns("__pycache__")
        )
        self.patch(config, "ALGO_DIR", algo_dir)
        tech_dir = self.tmp_path / "tech"
        shutil.copytree(FIXTURES / "tech", tech_dir)
        self.patch(config, "TECH_DIR", tech_dir)
        self.patch(config, "REFERENCE_DIR", self.tmp_path / "reference")
        problems.conventions_html.cache_clear()
