"""The site build: the landing page, both sections side by side, and a skills zip that can never
carry anyone's own job-search data."""

from __future__ import annotations

import importlib.util
import re
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


site_build = load("site_build", REPO / "build.py")
jobs_build = site_build.jobs


class SiteBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.out = cls.tmp / "site"
        site_build.build(cls.out, runtimes=False)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_layout(self):
        for rel in ("index.html", ".nojekyll", "practice/index.html", "practice/data.json", "jobs/index.html",
                    "jobs/jobs.js", "jobs/tracker-worker.js", "jobs/job-search.zip",
                    "jobs/py/job_tracker.py", "jobs/py/gmail_message.py", "jobs/py/tracker_api.py",
                    "jobs/finder.js", "jobs/finder-data.js", "jobs/sample-postings.json"):
            self.assertTrue((self.out / rel).is_file(), rel)

    def test_landing_page_sends_old_links_to_practice(self):
        html = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertIn('location.replace(`practice/${location.hash}`)', html)
        self.assertIn('addEventListener("hashchange", toPractice)', html)
        self.assertIn('href="practice/"', html)
        self.assertIn('href="jobs/"', html)

    def test_urls_are_relative(self):
        """GitHub Pages serves the site under /<repo>/, so nothing may point at the domain's root."""
        for page in ("index.html", "jobs/index.html"):
            html = (self.out / page).read_text(encoding="utf-8")
            self.assertEqual(re.findall(r'(?:href|src)="/[^/]', html), [], page)
        worker = (self.out / "jobs" / "tracker-worker.js").read_text(encoding="utf-8")
        self.assertIn('"../practice/vendor/pyodide/pyodide.mjs"', worker)
        self.assertIn('href="../practice/styles.css"', (self.out / "jobs" / "index.html").read_text(encoding="utf-8"))

    def test_the_jobs_page_runs_the_tracker_it_was_built_with(self):
        for name in jobs_build.TRACKER_FILES:
            self.assertEqual((self.out / "jobs" / "py" / name).read_bytes(), (jobs_build.TRACKER / name).read_bytes())

    def test_the_job_finder_sample_is_the_kits_example(self):
        self.assertEqual((self.out / "jobs" / "sample-postings.json").read_bytes(), jobs_build.SAMPLE_POSTINGS.read_bytes())

    def test_zip_holds_the_kit_under_one_folder(self):
        names = zipfile.ZipFile(self.out / "jobs" / "job-search.zip").namelist()
        self.assertTrue(all(n.startswith("job-search/") for n in names))
        for skill in ("job-find", "job-apply", "job-answers", "job-contacts", "interview-prep"):
            self.assertIn(f"job-search/skills/{skill}/SKILL.md", names)
        for rel in ("README.md", "profile.schema.json", ".gitignore", "examples/reference/profile.yaml"):
            self.assertIn(f"job-search/{rel}", names)


class KitZip(unittest.TestCase):
    """Someone's own data in the kit folder (it's where the skills keep it) stays out of the zip."""

    def test_personal_files_are_left_out(self):
        with tempfile.TemporaryDirectory() as d:
            kit = Path(d) / "job-search"
            shutil.copytree(jobs_build.KIT, kit, ignore=shutil.ignore_patterns("__pycache__"))
            for rel in ("reference/profile.yaml", "reference/resume.pdf", "applications/x/job.md", "tracker.csv", "postings.json",
                        "guides/northwind-interview-guide.md", ".env", "skills/settings.local.json",
                        "skills/job-apply/scripts/__pycache__/tracker.cpython-312.pyc", "emails.json"):
                (kit / rel).parent.mkdir(parents=True, exist_ok=True)
                (kit / rel).write_text("private", encoding="utf-8")
            with mock.patch.object(jobs_build, "KIT", kit):
                jobs_build.write_kit(Path(d) / "kit.zip")
            names = zipfile.ZipFile(Path(d) / "kit.zip").namelist()
            leaked = [n for n in names if n.endswith(("profile.yaml", "resume.pdf", "job.md", "tracker.csv", ".md", ".env",
                                                         ".json", ".pyc"))
                      and not n.startswith(("job-search/examples/", "job-search/skills/"))
                      and n not in ("job-search/README.md", "job-search/profile.schema.json",
                                    "job-search/.vscode/settings.json")]
            self.assertEqual(leaked, [])
            self.assertNotIn("job-search/skills/settings.local.json", names)
            self.assertFalse(any("__pycache__" in n for n in names))


if __name__ == "__main__":
    unittest.main(verbosity=2)
