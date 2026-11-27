"""The site build: relative URLs, a complete bundle, the test files the browser runs, the lint
settings, and the pinned WebAssembly runtimes."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path
from unittest import mock

from support import EnvCase, TempDirCase

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import build_static  # noqa: E402

from swe_prac import config  # noqa: E402


class StaticBuildTests(EnvCase):
    def setUp(self) -> None:
        super().setUp()
        self.out = self.tmp_path / "site"
        build_static.build(self.out, runtimes=False)

    def data(self) -> dict:
        return json.loads((self.out / "data.json").read_text(encoding="utf-8"))

    def test_index_uses_relative_urls_and_loads_the_app_as_a_module(self):
        html = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("/static/", html)  # a Pages site lives under /<repo>/, not at the root
        self.assertNotIn('src="/', html)
        self.assertIn('<script type="module" src="app.js"></script>', html)
        for name in (
            "app.js",
            "backend.js",
            "python.js",
            "py-worker.js",
            "py-job.js",
            "lint.js",
            "styles.css",
            "data.json",
            ".nojekyll",
        ):
            self.assertTrue((self.out / name).exists(), name)
        self.assertFalse((self.out / "static-api.js").exists())

    def test_bundle_has_every_view_the_ui_needs(self):
        data = self.data()
        self.assertEqual(data["levels"], [1, 2, 3, 4])
        self.assertTrue(data["conventions_html"])
        (item,) = data["problems"]
        self.assertEqual(sorted(item["tests_source"]), ["1", "2", "3", "4"])
        self.assertEqual([lv["level"] for lv in item["levels"]], [1, 2, 3, 4])
        for key in ("starter_code", "scratch_starter", "hints_html", "analysis_html"):
            self.assertTrue(item[key], key)

    def test_bundle_has_the_system_design_section(self):
        design = self.data()["design"]
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

    def test_bundle_has_the_algorithms_track(self):
        algo = self.data()["algo"]
        self.assertEqual(
            [p["problem"]["id"] for p in algo["problems"]], ["x01_pair_sum", "x02_reverse_list"]
        )
        self.assertEqual(algo["minutes"], {"Easy": 20, "Medium": 30, "Hard": 40})
        self.assertEqual(algo["patterns"], ["Hashing", "Linked lists", "Two pointers"])
        item = algo["problems"][0]
        self.assertEqual([e["name"] for e in item["examples"]], ["Example 1", "Example 2"])
        self.assertEqual(item["params"], ["nums", "target"])
        for key in (
            "statement_html",
            "starter_code",
            "scratch_starter",
            "hints_html",
            "explanation_html",
        ):
            self.assertTrue(item[key], key)
        self.assertEqual(item["foundations"][0]["href"], "#/algo/learn/basics/hashing")
        for name in ("algo.js", "learn.js", "common.js"):
            self.assertTrue((self.out / name).exists(), name)

    def test_bundle_has_the_foundations_pages(self):
        found = self.data()["foundations"]
        self.assertEqual(found["design"], {"cards": [], "pages": {}})  # the fixture has none
        self.assertEqual([c["slug"] for c in found["algo"]["cards"]], ["basics"])
        page = found["algo"]["pages"]["basics"]
        self.assertEqual((page["title"], page["prev"], page["next"]), ("Basics", None, None))
        self.assertIn('id="hashing"', page["html"])
        self.assertEqual([s["id"] for s in page["toc"]], ["hashing", "two-pointers"])

    def test_bundle_has_the_tech_pages_with_their_code(self):
        tech = self.data()["foundations"]["tech"]
        self.assertEqual([c["slug"] for c in tech["cards"]], ["demo"])
        html = tech["pages"]["demo"]["html"]
        self.assertIn('<div class="code-file">demo/hello.ts</div>', html)
        self.assertIn("&lt;world&gt;", html)
        self.assertEqual(tech["pages"]["demo"]["project"], {"folder": "demo", "files": 1})
        # The file browser's copy of the project.
        (file,) = tech["projects"]["demo"]["files"]
        self.assertEqual((file["path"], file["lang"]), ("hello.ts", "ts"))
        self.assertIn("<world>", file["text"])
        backend = (self.out / "backend.js").read_text(encoding="utf-8")
        self.assertIn(r"/^\/api\/(tech)\/pages$/", backend)
        self.assertIn(r"/^\/api\/(tech)\/pages\/([\w-]+)\/files$/", backend)
        for lang in ("typescript", "css", "html", "markdown"):
            path = self.out / "vendor" / "monaco" / "vs" / "basic-languages" / lang / f"{lang}.js"
            self.assertTrue(path.exists(), lang)

    def test_each_problem_has_a_test_file_with_its_hidden_tests(self):
        source = self.tmp_path / "problems" / "p0_counter" / "tests.json"
        tests = json.loads(source.read_text(encoding="utf-8"))["tests"]
        self.assertTrue([t for t in tests if t["visibility"] == "hidden"], "fixture needs some")
        coding = json.loads((self.out / "tests/coding/p0_counter.json").read_text("utf-8"))
        self.assertEqual(coding["class_name"], "Counter")
        self.assertEqual([t["id"] for t in coding["tests"]], [t["id"] for t in tests])

        for problem in ("x01_pair_sum", "x02_reverse_list"):
            with self.subTest(problem=problem):
                source = self.tmp_path / "algorithms" / problem / "tests.json"
                hidden = json.loads(source.read_text(encoding="utf-8"))["hidden"]
                self.assertTrue(hidden, f"{problem} should have hidden tests")
                path = self.out / "tests" / "algo" / f"{problem}.json"
                algo = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(algo["class_name"], "Solution")
                self.assertIn("compare", json.dumps(algo["options"]))
                names = {t["name"] for t in algo["tests"]}
                self.assertTrue({c["name"] for c in hidden} <= names)

    def test_hidden_tests_stay_out_of_the_page_bundle(self):
        """data.json loads on every page; the hidden tests load only when you run code."""
        exported = (self.out / "data.json").read_text(encoding="utf-8")
        tests = json.loads(
            (self.tmp_path / "problems" / "p0_counter" / "tests.json").read_text(encoding="utf-8")
        )["tests"]
        for test in tests:
            if test["visibility"] == "hidden":
                self.assertNotIn(test["name"], exported)
        for problem in ("x01_pair_sum", "x02_reverse_list"):
            path = self.tmp_path / "algorithms" / problem / "tests.json"
            for case in json.loads(path.read_text(encoding="utf-8"))["hidden"]:
                self.assertNotIn(case["name"], exported)

    def test_the_runner_and_scratch_helpers_ship_as_python_files(self):
        self.assertEqual(
            (self.out / "py" / "runner.py").read_bytes(), config.RUNNER_PATH.read_bytes()
        )
        self.assertEqual(
            (self.out / "py" / "helpers.py").read_bytes(), config.SCRATCH_HELPERS_PATH.read_bytes()
        )

    def test_the_lint_settings_merge_the_extended_config(self):
        ruff = self.data()["ruff"]
        coding, algo = ruff["coding"], ruff["algo"]
        self.assertNotIn("extend", algo)
        self.assertEqual(algo["lint"]["select"], coding["lint"]["select"])
        self.assertEqual(algo["lint"]["ignore"][: len(coding["lint"]["ignore"])],
                         coding["lint"]["ignore"])  # fmt: skip
        self.assertIn("N802", algo["lint"]["ignore"])
        self.assertNotIn("N802", coding["lint"]["ignore"])
        self.assertEqual(algo["line-length"], coding["line-length"])

    def test_runtimes_are_left_out_when_asked(self):
        self.assertFalse((self.out / "vendor" / "pyodide").exists())
        self.assertFalse((self.out / "vendor" / "ruff").exists())


def _tgz(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(f"package/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _integrity(data: bytes) -> str:
    return "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()


class RuntimeTests(TempDirCase):
    """The npm tarballs: checked against the pinned hash, cached, and only the listed files
    unpacked. Everything comes from the cache here, so nothing is downloaded."""

    def setUp(self) -> None:
        super().setUp()
        self.patch(build_static, "CACHE_DIR", self.tmp_path / "cache")
        self.tarball = _tgz({"run.js": b"js", "run.wasm": b"\0asm", "extra.txt": b"x"})
        (self.tmp_path / "cache").mkdir()
        (self.tmp_path / "cache" / "fake-1.0.0.tgz").write_bytes(self.tarball)
        self.spec = {
            "package": "@scope/fake",
            "version": "1.0.0",
            "integrity": _integrity(self.tarball),
            "files": ["run.js", "run.wasm"],
            "notice": "Fake {version}.\n",
        }
        self.enterContext(mock.patch.dict(build_static.RUNTIMES, {"fake": self.spec}))

    def test_only_the_listed_files_are_unpacked_with_a_notice(self):
        build_static.write_runtime("fake", self.tmp_path / "site")
        dest = self.tmp_path / "site" / "vendor" / "fake"
        names = sorted(p.name for p in dest.iterdir())
        self.assertEqual(names, ["README.txt", "run.js", "run.wasm"])
        self.assertEqual((dest / "run.wasm").read_bytes(), b"\0asm")
        self.assertEqual((dest / "README.txt").read_text(encoding="utf-8"), "Fake 1.0.0.\n")

    def test_a_tarball_with_the_wrong_hash_is_refused(self):
        self.spec["integrity"] = _integrity(b"something else")
        with self.assertRaises(SystemExit) as caught:
            build_static.write_runtime("fake", self.tmp_path / "site")
        self.assertIn("sha512 is wrong", str(caught.exception))

    def test_the_pinned_runtimes_name_the_files_the_browser_loads(self):
        worker = (config.STATIC_DIR / "py-worker.js").read_text(encoding="utf-8")
        lint = (config.STATIC_DIR / "lint.js").read_text(encoding="utf-8")
        self.assertIn("./vendor/pyodide/pyodide.mjs", worker)
        self.assertIn("./vendor/ruff/ruff_wasm.js", lint)
        self.assertIn("pyodide.mjs", build_static.RUNTIMES["pyodide"]["files"])
        self.assertIn("ruff_wasm_bg.wasm", build_static.RUNTIMES["ruff"]["files"])
        requirements = (config.PACKAGE_DIR.parent / "requirements.txt").read_text("utf-8")
        self.assertIn(f"ruff=={build_static.RUNTIMES['ruff']['version']}", requirements)


class RuffSettingsTests(TempDirCase):
    def test_a_child_config_adds_to_the_parents_ignores_and_wins_on_other_keys(self):
        (self.tmp_path / "base.toml").write_text(
            'line-length = 100\n[lint]\nselect = ["E", "N"]\nignore = ["E501"]\n'
            '[format]\nquote-style = "double"\n',
            encoding="utf-8",
        )
        (self.tmp_path / "child.toml").write_text(
            'extend = "base.toml"\nline-length = 80\n[lint]\nignore = ["N802"]\n',
            encoding="utf-8",
        )
        self.assertEqual(
            build_static.ruff_settings(self.tmp_path / "child.toml"),
            {
                "line-length": 80,
                "lint": {"select": ["E", "N"], "ignore": ["E501", "N802"]},
                "format": {"quote-style": "double"},
            },
        )
