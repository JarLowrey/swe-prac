"""Tech investigations as the site build publishes them, and the ```include block they use,
against the fixture page."""

from __future__ import annotations

import unittest

from support import EnvCase

from swe_prac import config, pages, tech


def cards() -> list[dict]:
    return [tech.card(p) for p in pages.list_pages(tech.pages_dir())]


def project(slug: str) -> dict | None:
    return tech.project(pages.get(tech.pages_dir(), slug))


class TechPageTests(EnvCase):
    def test_the_list_has_one_card_per_page(self):
        (card,) = cards()
        self.assertEqual(card["slug"], "demo")
        self.assertEqual(card["title"], "Demo investigation")
        self.assertTrue(card["summary"].startswith("A tiny tech page"))
        self.assertEqual([s["id"] for s in card["sections"]], ["the-code", "running-it"])

    def test_a_page_shows_the_included_file_under_its_path(self):
        page = tech.page_payload("demo")
        html = page["html"]
        self.assertIn('<div class="code-file">demo/hello.ts</div>', html)
        self.assertIn('<code class="language-ts">', html)
        # The whole file, escaped, including the ``` in its first line.
        self.assertIn("a fence in it: ```", html)
        self.assertIn("&lt;world&gt;", html)
        self.assertNotIn("```include", html)
        self.assertEqual((page["prev"], page["next"]), (None, None))

    def test_an_unknown_page_is_an_error(self):
        with self.assertRaises(pages.PageNotFound):
            tech.page_payload("nope")


class ProjectFilesTests(EnvCase):
    """The file browser's copy of the project: the folder named after the page's slug."""

    def test_cards_and_pages_name_the_project(self):
        (card,) = cards()
        self.assertEqual(card["project"], {"folder": "demo", "files": 1})
        self.assertEqual(tech.page_payload("demo")["project"], {"folder": "demo", "files": 1})

    def test_a_file_comes_with_its_text_and_the_sections_that_show_it(self):
        info = project("demo")
        self.assertEqual((info["slug"], info["folder"]), ("demo", "demo"))
        self.assertEqual(info["title"], "Demo investigation")
        (file,) = info["files"]
        self.assertEqual((file["path"], file["lang"], file["note"]), ("hello.ts", "ts", None))
        self.assertIn("<world>", file["text"])
        self.assertEqual(file["size"], (config.TECH_DIR / "demo" / "hello.ts").stat().st_size)
        self.assertEqual(file["sections"], [{"id": "the-code", "title": "The code"}])

    def test_build_output_secrets_and_gitignored_files_are_left_out(self):
        demo = config.TECH_DIR / "demo"
        for name in (
            "node_modules/pkg/index.js",
            "dist/assets/app.js",
            "src/deep/node_modules/x.js",
            ".env",
            ".env.production",
            "settings.local",
            "debug.log",
            "tmp/scratch.ts",
            "src/b.css",
            ".env.example",
        ):
            (demo / name).parent.mkdir(parents=True, exist_ok=True)
            (demo / name).write_text("x\n", encoding="utf-8")
        (demo / ".gitignore").write_text("# local\n*.log\n/tmp/\n!keep.log\n", encoding="utf-8")
        paths = [f["path"] for f in project("demo")["files"]]
        self.assertEqual(paths, [".env.example", ".gitignore", "hello.ts", "src/b.css"])

    def test_binary_and_large_files_are_listed_without_their_text(self):
        demo = config.TECH_DIR / "demo"
        (demo / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\xff\xfe")
        (demo / "big.json").write_text("[" + "0," * 60_000 + "0]", encoding="utf-8")
        by_path = {f["path"]: f for f in project("demo")["files"]}
        self.assertIsNone(by_path["logo.png"]["text"])
        self.assertIn("binary", by_path["logo.png"]["note"])
        self.assertIsNone(by_path["big.json"]["text"])
        self.assertIn("117.2 KB, too big", by_path["big.json"]["note"])
        self.assertEqual(by_path["big.json"]["lang"], "json")

    def test_a_page_without_a_project_folder_has_no_files(self):
        (config.TECH_DIR / "02_bare.md").write_text(
            "# Bare\n\nA page with no project.\n\n## Notes\n\nText.\n", encoding="utf-8"
        )
        self.assertEqual([c["project"] for c in cards()], [{"folder": "demo", "files": 1}, None])
        self.assertIsNone(tech.page_payload("bare")["project"])
        self.assertIsNone(project("bare"))
        bundle = tech.bundle()
        self.assertEqual(sorted(bundle["pages"]), ["bare", "demo"])
        self.assertEqual(sorted(bundle["projects"]), ["demo"])


class IncludeTests(EnvCase):
    def _render(self, name: str) -> str:
        return pages.expand_includes(f"```include\n{name}\n```\n", config.TECH_DIR)

    def test_a_missing_file_is_an_error_box(self):
        out = self._render("demo/missing.ts")
        self.assertIn('class="diagram-error"', out)
        self.assertIn("no file demo/missing.ts", out)

    def test_a_path_outside_the_folder_is_refused(self):
        outside = config.TECH_DIR.parent / "secret.txt"
        outside.write_text("do not show", encoding="utf-8")
        out = self._render("../secret.txt")
        self.assertIn('class="diagram-error"', out)
        self.assertNotIn("do not show", out)

    def test_the_fence_is_longer_than_any_backticks_in_the_file(self):
        out = self._render("demo/hello.ts")
        self.assertTrue(out.split("\n")[2].startswith("````ts"), out)
        self.assertTrue(out.rstrip("\n").endswith("\n````"), out)


if __name__ == "__main__":
    unittest.main()
