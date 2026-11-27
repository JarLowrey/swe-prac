#!/usr/bin/env python3
"""
Tests for the job-find skill's postings.py: search URLs, reading what the cards show (dates, pay,
workplace), clean links, merging runs without duplicates, and the sample examples/postings.json
that the site's Job finder page imports.

  python -m unittest discover -s jobs/tests
"""
from __future__ import annotations

import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

KIT = Path(__file__).resolve().parent.parent / "job-search"
SCRIPT = KIT / "skills" / "job-find" / "scripts" / "postings.py"
SAMPLE = KIT / "examples" / "postings.json"

spec = importlib.util.spec_from_file_location("postings", SCRIPT)
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

DAY = dt.date(2026, 11, 27)


def batch(source="linkedin", postings=(), ran_at="2026-11-27T15:00:00Z", **kw):
    return {"source": source, "query": "backend engineer", "location": "Denver, CO", "remote": False, "days": 1,
            "url": "https://jobs.example.com/search", "ran_at": ran_at, "note": "", "postings": list(postings), **kw}


def card(id="4012345678", **kw):
    return {"id": id, "url": "", "title": "Senior Backend Engineer", "company": "Northwind",
            "location": "Denver, CO (Hybrid)", "posted_text": "2 days ago", "salary_text": "", "easy_apply": None, **kw}


class SearchUrls(unittest.TestCase):
    def q(self, url):
        return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}

    def test_linkedin_filters_by_seconds_sorts_newest_and_encodes(self):
        url = P.search_url("linkedin", "senior  backend engineer", "Denver, CO", days=7)
        self.assertTrue(url.startswith("https://www.linkedin.com/jobs/search/?"))
        self.assertIn("keywords=senior%20backend%20engineer", url)
        self.assertEqual(self.q(url), {"keywords": "senior backend engineer", "location": "Denver, CO",
                                       "f_TPR": "r604800", "sortBy": "DD"})

    def test_linkedin_remote_and_second_page(self):
        q = self.q(P.search_url("linkedin", "backend engineer", "United States", days=1, remote=True, page=1))
        self.assertEqual((q["f_TPR"], q["f_WT"], q["start"], q["location"]), ("r86400", "2", "25", "United States"))

    def test_indeed_uses_fromage_and_remote_as_the_place(self):
        q = self.q(P.search_url("indeed", "backend engineer", "Denver, CO", days=3))
        self.assertEqual(q, {"q": "backend engineer", "l": "Denver, CO", "fromage": "3", "sort": "date"})
        q = self.q(P.search_url("indeed", "backend engineer", "United States", days=14, remote=True, page=2))
        self.assertEqual((q["l"], q["fromage"], q["start"]), ("Remote", "14", "20"))
        self.assertTrue(P.search_url("indeed", "a&b", "").startswith("https://www.indeed.com/jobs?q=a%26b&"))

    def test_bad_days_or_source_refused(self):
        with self.assertRaises(ValueError):
            P.search_url("linkedin", "x", days=5)
        with self.assertRaises(ValueError):
            P.search_url("monster", "x")

    def test_both_sources_listed(self):
        out = P.search_urls("backend engineer", "Denver, CO", 1)
        self.assertEqual([u["source"] for u in out], ["linkedin", "indeed"])
        self.assertEqual(len(P.search_urls("x", source="indeed")), 1)


class PostedDates(unittest.TestCase):
    def test_each_form(self):
        cases = {
            "Just posted": "2026-11-27", "Today": "2026-11-27", "Active today": "2026-11-27",
            "5 minutes ago": "2026-11-27", "3 hours ago": "2026-11-27", "1 day ago": "2026-11-26",
            "2 days ago": "2026-11-25", "Posted 5 days ago": "2026-11-22", "Reposted 2 weeks ago": "2026-11-13",
            "1 month ago": "2026-10-28", "30+ days ago": "2026-10-28", "Yesterday": "2026-11-26",
            "": "", "Promoted": "",
        }
        for text, want in cases.items():
            self.assertEqual(P.parse_posted(text, DAY), want, text)

    def test_ran_at_date_is_the_reference(self):
        self.assertEqual(P.parse_date("2026-11-27T23:59:00Z"), DAY)
        self.assertEqual(P.parse_date("2026-11-27"), DAY)


class Salaries(unittest.TestCase):
    def test_each_form(self):
        cases = {
            "$150K/yr - $190K/yr": (150000, 190000),
            "$150,000 - $190,000 a year": (150000, 190000),
            "$60 - $75 an hour": (124800, 156000),
            "$9,000 a month": (108000, 108000),
            "Up to $120,000 a year": (120000, 120000),
            "From $1.2M/yr": (1200000, 1200000),
            "$45 - $60": (93600, 124800),
            "US$130,000 a year": (130000, 130000),
        }
        for text, want in cases.items():
            self.assertEqual(P.parse_salary(text), want, text)

    def test_junk_and_other_currencies_are_none(self):
        for text in ("", "Competitive", "CA$120K/yr", "£50,000 a year", "€60,000", "$", "$5 an item",
                     "401(k) matching"):
            self.assertEqual(P.parse_salary(text), (None, None), text)


class Workplace(unittest.TestCase):
    def test_markers_parsed_and_removed(self):
        cases = {
            "Denver, CO (Hybrid)": ("hybrid", "Denver, CO"),
            "United States (Remote)": ("remote", "United States"),
            "Denver, CO (On-site)": ("onsite", "Denver, CO"),
            "Hybrid work in Denver, CO": ("hybrid", "Denver, CO"),
            "Remote in Boulder, CO": ("remote", "Boulder, CO"),
            "Remote": ("remote", ""),
            "Denver, CO 80202": ("", "Denver, CO 80202"),
            "": ("", ""),
        }
        for loc, want in cases.items():
            self.assertEqual(P.parse_workplace(loc), want, loc)

    def test_title_is_the_fallback(self):
        self.assertEqual(P.parse_workplace("Denver, CO", "Senior Engineer (Remote)"), ("remote", "Denver, CO"))
        self.assertEqual(P.parse_workplace("Denver, CO (On-site)", "Remote-first team"), ("onsite", "Denver, CO"))


class Links(unittest.TestCase):
    def test_ids_from_urls(self):
        self.assertEqual(P.source_id("linkedin", "", "https://www.linkedin.com/jobs/view/4012345678/?trk=x"), "4012345678")
        self.assertEqual(P.source_id("linkedin", "", "https://www.linkedin.com/jobs/view/engineer-ii-2-at-acme-4012/"), "4012")
        self.assertEqual(P.source_id("linkedin", "", "https://www.linkedin.com/jobs/search/?currentJobId=399"), "399")
        self.assertEqual(P.source_id("indeed", "", "https://www.indeed.com/rc/clk?jk=ab12cd&from=serp"), "ab12cd")
        self.assertEqual(P.source_id("indeed", "indeed:ab12", ""), "ab12")
        self.assertEqual(P.source_id("indeed", "", "https://www.indeed.com/jobs"), "")

    def test_source_links_become_canonical_https(self):
        self.assertEqual(P.canonical_url("linkedin", "4012", "https://www.linkedin.com/jobs/view/4012/?trk=abc&refId=z"),
                         "https://www.linkedin.com/jobs/view/4012/")
        self.assertEqual(P.canonical_url("linkedin", "4012", "http://linkedin.com/jobs/view/4012"),
                         "https://www.linkedin.com/jobs/view/4012/")
        self.assertEqual(P.canonical_url("indeed", "ab12", "https://www.indeed.com/rc/clk?jk=ab12&from=serp&tk=1"),
                         "https://www.indeed.com/viewjob?jk=ab12")
        self.assertEqual(P.canonical_url("indeed", "ab12", ""), "https://www.indeed.com/viewjob?jk=ab12")

    def test_other_links_keep_https_only_without_tracking(self):
        self.assertEqual(P.canonical_url("indeed", "ab12", "https://jobs.example.com/x?utm_source=a&ref=b&team=7"),
                         "https://jobs.example.com/x?team=7")
        self.assertEqual(P.canonical_url("indeed", "ab12", "http://jobs.example.com/x"), "https://www.indeed.com/viewjob?jk=ab12")
        self.assertEqual(P.canonical_url("indeed", "ab12", "javascript:alert(1)"), "https://www.indeed.com/viewjob?jk=ab12")


class Merge(unittest.TestCase):
    def test_new_posting_is_normalized(self):
        data = P.empty()
        c = P.add_batch(data, batch(postings=[card(salary_text="$150K/yr - $190K/yr", easy_apply=True)]), now="N")
        self.assertEqual(c, {"found": 1, "new": 1, "seen": 0, "also_on": 0, "skipped": 0})
        p = data["postings"][0]
        self.assertEqual(p["id"], "linkedin:4012345678")
        self.assertEqual(p["url"], "https://www.linkedin.com/jobs/view/4012345678/")
        self.assertEqual((p["workplace"], p["location"], p["posted"]), ("hybrid", "Denver, CO", "2026-11-25"))
        self.assertEqual((p["salary_min"], p["salary_max"], p["easy_apply"]), (150000, 190000, True))
        self.assertEqual((p["first_seen"], p["last_seen"], p["also_on"], p["query"]),
                         ("2026-11-27", "2026-11-27", [], "backend engineer"))
        self.assertEqual(list(p), list(P.POSTING_KEYS))
        self.assertEqual(data["updated_at"], "N")
        self.assertEqual(data["searches"][0]["found"], 1)
        self.assertEqual(list(data["searches"][0]), list(P.SEARCH_KEYS))

    def test_same_id_updates_last_seen_and_fills_blanks_keeping_first_seen(self):
        data = P.empty()
        P.add_batch(data, batch(postings=[card()], ran_at="2026-11-20T10:00:00Z"))
        c = P.add_batch(data, batch(postings=[card(salary_text="$150K/yr", title="Changed", posted_text="1 week ago")],
                                    ran_at="2026-11-27T10:00:00Z"))
        self.assertEqual((c["new"], c["seen"]), (0, 1))
        self.assertEqual(len(data["postings"]), 1)
        p = data["postings"][0]
        self.assertEqual((p["first_seen"], p["last_seen"]), ("2026-11-20", "2026-11-27"))
        self.assertEqual((p["title"], p["posted"], p["salary_min"]), ("Senior Backend Engineer", "2026-11-18", 150000))

    def test_same_job_on_the_other_site_goes_in_also_on(self):
        data = P.empty()
        P.add_batch(data, batch(postings=[card(company="Northwind, Inc.")]))
        c = P.add_batch(data, batch("indeed", postings=[card("ab12cd", title="Sr. Backend Engineer", company="NORTHWIND",
                                                           location="Hybrid work in Denver, CO")]))
        self.assertEqual((c["new"], c["also_on"]), (0, 1))
        self.assertEqual(len(data["postings"]), 1)
        self.assertEqual(data["postings"][0]["also_on"], ["indeed:ab12cd"])
        # Seen again on Indeed later: counted as seen, still one posting.
        c = P.add_batch(data, batch("indeed", postings=[card("ab12cd", company="Northwind", location="Denver, CO")],
                                    ran_at="2026-11-29T09:00:00Z"))
        self.assertEqual((c["seen"], len(data["postings"]), data["postings"][0]["last_seen"]), (1, 1, "2026-11-29"))

    def test_remote_matches_remote_anywhere(self):
        data = P.empty()
        P.add_batch(data, batch(postings=[card(location="United States (Remote)")]))
        P.add_batch(data, batch("indeed", postings=[card("ff01", location="Remote")]))
        self.assertEqual(data["postings"][0]["also_on"], ["indeed:ff01"])

    def test_different_place_or_same_site_stays_separate(self):
        data = P.empty()
        P.add_batch(data, batch(postings=[card(), card("4099", location="Boulder, CO (Hybrid)")]))
        P.add_batch(data, batch("indeed", postings=[card("ab12", location="Austin, TX")]))
        P.add_batch(data, batch(postings=[card("4100")]))  # a second LinkedIn opening, same title and place
        self.assertEqual(len(data["postings"]), 4)

    def test_cards_without_id_or_title_are_skipped(self):
        data = P.empty()
        c = P.add_batch(data, batch(postings=[card(id="", url=""), card(title=""), "junk"]))
        self.assertEqual((c["found"], c["skipped"], len(data["postings"])), (3, 3, 0))

    def test_sorted_newest_posting_first_and_searches_capped(self):
        data = P.empty()
        P.add_batch(data, batch(postings=[card("1", posted_text="5 days ago", title="A"),
                                          card("2", posted_text="Just posted", title="B"),
                                          card("3", posted_text="", title="C")]))
        self.assertEqual([p["id"] for p in data["postings"]], ["linkedin:2", "linkedin:1", "linkedin:3"])
        for _ in range(P.MAX_SEARCHES + 5):
            P.add_batch(data, batch(postings=[]))
        self.assertEqual(len(data["searches"]), P.MAX_SEARCHES)

    def test_unknown_source_refused(self):
        with self.assertRaises(ValueError):
            P.add_batch(P.empty(), batch("monster"))


class CommandLine(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = P.main(list(argv))
        return code, out.getvalue()

    def test_add_twice_is_idempotent_and_writes_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "postings.json"
            b = Path(tmp) / "b.json"
            b.write_text(json.dumps([batch(postings=[card()]), batch("indeed", postings=[card("ab12")])]), encoding="utf-8")
            code, out = self.run_cli("--file", str(f), "add", str(b))
            self.assertEqual(code, 0)
            self.assertIn("1 new", out)
            self.assertIn("1 also on the other site", out)
            first = json.loads(f.read_text(encoding="utf-8"))
            self.run_cli("--file", str(f), "add", str(b))
            again = json.loads(f.read_text(encoding="utf-8"))
            self.assertEqual(again["postings"], first["postings"])
            self.assertFalse((Path(tmp) / "postings.json.tmp").exists())
            code, out = self.run_cli("--file", str(f), "list")
            self.assertIn("Northwind", out)
            self.assertIn("linkedin +", out)

    def test_urls_prints_json(self):
        _, out = self.run_cli("urls", "--query", "backend engineer", "--location", "Denver, CO", "--days", "3")
        urls = json.loads(out)
        self.assertEqual([u["source"] for u in urls], ["linkedin", "indeed"])
        self.assertTrue(all(u["url"].startswith("https://") for u in urls))

    def test_data_dir_prefers_env(self):
        old = os.environ.get("JOB_SEARCH_DIR")
        os.environ["JOB_SEARCH_DIR"] = str(KIT / "examples")
        try:
            self.assertEqual(P.postings_path(), KIT / "examples" / "postings.json")
        finally:
            if old is None:
                del os.environ["JOB_SEARCH_DIR"]
            else:
                os.environ["JOB_SEARCH_DIR"] = old


DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def check_contract(test: unittest.TestCase, data: dict) -> None:
    """What the site's Job finder page relies on, checked on every record."""
    test.assertEqual(data["version"], 1)
    test.assertIsInstance(data["updated_at"], str)
    ids = set()
    for s in data["searches"]:
        test.assertEqual(set(s), set(P.SEARCH_KEYS))
        test.assertIn(s["source"], P.SOURCES)
        test.assertIsInstance(s["found"], int)
        test.assertIsInstance(s["remote"], bool)
    for p in data["postings"]:
        test.assertEqual(list(p), list(P.POSTING_KEYS), p["id"])
        test.assertIn(p["source"], P.SOURCES)
        test.assertTrue(p["id"].startswith(p["source"] + ":"), p["id"])
        test.assertNotIn(p["id"], ids)
        ids.add(p["id"])
        test.assertTrue(p["url"].startswith("https://"), p["id"])
        for k in ("title", "company", "location", "posted_text", "salary_text", "query"):
            test.assertIsInstance(p[k], str, (p["id"], k))
        test.assertTrue(p["title"])
        test.assertIn(p["workplace"], ("remote", "hybrid", "onsite", ""))
        test.assertTrue(p["posted"] == "" or DATE.match(p["posted"]), p["id"])
        test.assertTrue(DATE.match(p["first_seen"]) and DATE.match(p["last_seen"]))
        test.assertLessEqual(p["first_seen"], p["last_seen"])
        for k in ("salary_min", "salary_max"):
            test.assertTrue(p[k] is None or isinstance(p[k], int), (p["id"], k))
        test.assertEqual(p["salary_min"] is None, p["salary_max"] is None)
        if p["salary_min"] is not None:
            test.assertLessEqual(p["salary_min"], p["salary_max"])
        test.assertIn(p["easy_apply"], (True, None))
        test.assertIsInstance(p["also_on"], list)
        for other in p["also_on"]:
            test.assertFalse(other.startswith(p["source"] + ":"), other)
            test.assertNotIn(other, ids)
            ids.add(other)


class SampleData(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SAMPLE.read_text(encoding="utf-8"))

    def test_matches_the_contract(self):
        check_contract(self, self.data)

    def test_has_what_the_charts_need(self):
        posts = self.data["postings"]
        self.assertGreaterEqual(len(posts), 30)
        self.assertEqual({p["source"] for p in posts}, set(P.SOURCES))
        self.assertGreaterEqual(len({p["company"] for p in posts}), 8)
        self.assertTrue(any(p["also_on"] for p in posts))
        self.assertTrue(any(p["salary_min"] is not None for p in posts))
        self.assertTrue(any(p["posted"] == "" for p in posts))
        self.assertEqual({p["workplace"] for p in posts} >= {"remote", "hybrid", "onsite"}, True)
        self.assertTrue(any(s["note"] for s in self.data["searches"]))

    def test_links_never_point_at_real_job_sites(self):
        text = SAMPLE.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"https?://[^\"]*(linkedin|indeed)\.com")
        for p in self.data["postings"]:
            self.assertTrue(p["url"].startswith("https://jobs.example.com/"), p["url"])

    def test_sample_round_trips_through_add(self):
        # Re-adding a run's batch of already-known cards changes nothing but last_seen-free fields.
        data = json.loads(json.dumps(self.data))
        before = {p["id"]: dict(p) for p in data["postings"]}
        p = data["postings"][0]
        sid = p["id"].split(":", 1)[1]
        P.add_batch(data, {"source": p["source"], "query": p["query"], "ran_at": p["last_seen"] + "T00:00:00Z",
                           "postings": [{"id": sid, "url": p["url"], "title": p["title"], "company": p["company"],
                                         "location": p["location"], "posted_text": p["posted_text"]}]})
        self.assertEqual(len(data["postings"]), len(before))
        self.assertEqual(data["postings"][0], before[p["id"]])


if __name__ == "__main__":
    unittest.main()
