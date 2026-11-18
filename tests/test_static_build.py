"""The static site build: relative URLs, a complete bundle, and no hidden-test leakage."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from support import EnvCase

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import build_static  # noqa: E402


class StaticBuildTests(EnvCase):
    def setUp(self) -> None:
        super().setUp()
        self.out = self.tmp_path / "site"
        build_static.build(self.out)

    def test_index_uses_relative_urls_and_the_static_backend(self):
        html = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("/static/", html)  # a Pages site lives under /<repo>/, not at the root
        self.assertLess(html.index("static-api.js"), html.index("app.js"))
        for name in ("static-api.js", "app.js", "styles.css", "data.json", ".nojekyll"):
            self.assertTrue((self.out / name).exists(), name)

    def test_bundle_has_every_view_the_ui_needs(self):
        data = json.loads((self.out / "data.json").read_text(encoding="utf-8"))
        self.assertEqual(data["levels"], [1, 2, 3, 4])
        self.assertTrue(data["conventions_html"])
        (item,) = data["problems"]
        self.assertEqual(sorted(item["tests_source"]), ["1", "2", "3", "4"])
        self.assertEqual([lv["level"] for lv in item["levels"]], [1, 2, 3, 4])
        for key in ("starter_code", "scratch_starter", "hints_html", "analysis_html"):
            self.assertTrue(item[key], key)

    def test_bundle_has_the_system_design_section(self):
        design = json.loads((self.out / "data.json").read_text(encoding="utf-8"))["design"]
        self.assertEqual([s["step"] for s in design["steps"]], [1, 2, 3])
        self.assertEqual(len(design["checklist"]), 3)
        self.assertEqual(design["time_limit"], 45 * 60)
        self.assertIn("test fixture", design["guide_html"])
        (item,) = design["questions"]
        self.assertEqual(item["question"]["id"], "d00_pastebin")
        self.assertEqual(item["hints"]["hard_part"], "Read-heavy traffic")
        self.assertEqual(len(item["key_points"]), 2)
        self.assertIn("Cache hot pastes", item["reference_html"])
        self.assertTrue((self.out / "design.js").exists())
        self.assertTrue((self.out / "diagram.js").exists())

    def test_bundle_has_the_foundations_pages(self):
        found = json.loads((self.out / "data.json").read_text(encoding="utf-8"))["foundations"]
        self.assertEqual(found, {"design": {"cards": [], "pages": {}}})  # the fixture has none

    def test_hidden_tests_are_not_exported(self):
        tests = json.loads(
            (self.tmp_path / "problems" / "p0_counter" / "tests.json").read_text(encoding="utf-8")
        )["tests"]
        hidden = [t for t in tests if t["visibility"] == "hidden"]
        self.assertTrue(hidden, "fixture should have hidden tests")
        exported = (self.out / "data.json").read_text(encoding="utf-8")
        for test in hidden:
            self.assertNotIn(test["name"], exported)
