"""
Tests for gmail_message.py and tracker_api.py: Gmail API messages (format=raw) as records, and
the JSON functions the Jobs page calls in the browser. Synthetic messages only.

  python -m unittest discover -s jobs/tests
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import os
import sys
import unittest
from email.message import EmailMessage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tracker"))
import gmail_message as gm  # noqa: E402
import job_tracker as jt  # noqa: E402
import tracker_api  # noqa: E402


def ms(y, mo, d, h=12) -> int:
    return int(dt.datetime(y, mo, d, h, tzinfo=dt.timezone.utc).timestamp() * 1000)


def make_mail(subject, body, sender="no-reply@example.com", html=None, date=None, attach=None,
              charset="utf-8", html_only=False, stub=None) -> bytes:
    m = EmailMessage()
    m["From"] = sender
    m["To"] = "candidate@example.com"
    m["Subject"] = subject
    if date:
        m["Date"] = date
    if html is not None and html_only:          # a message with no plain-text part at all
        m.set_content(html, subtype="html")
    elif html is not None and stub is not None:  # plain part is a stub, e.g. "view in browser"
        m.set_content(stub)
        m.add_alternative(html, subtype="html")
    elif html is not None:
        m.set_content(body)
        m.add_alternative(html, subtype="html")
    else:
        m.set_content(body, charset=charset)
    if attach:
        m.add_attachment(attach, maintype="application", subtype="pdf", filename="offer.pdf")
    return m.as_bytes()


def api_message(raw: bytes, mid="18c0a1", thread="18c0a0", labels=("INBOX",), when=None, pad=False) -> dict:
    """What users.messages.get?format=raw returns. Gmail leaves the base64url padding off."""
    enc = base64.urlsafe_b64encode(raw).decode()
    return {"id": mid, "threadId": thread, "labelIds": list(labels),
            "internalDate": str(when or ms(2026, 10, 25)), "raw": enc if pad else enc.rstrip("=")}


class FromApi(unittest.TestCase):
    def test_plain_message_fields(self):
        m = gm.from_api(api_message(make_mail("Thank you for applying to Acme", "Thanks for applying to Acme.",
                                              '"Acme Jobs" <jobs@acme.example>'),
                                    labels=["INBOX", "IMPORTANT", "Label_7"]), "candidate@example.com")
        self.assertEqual((m["id"], m["threadId"], m["from"]), ("18c0a1", "18c0a0", "jobs@acme.example"))
        self.assertEqual(m["labels"], ["INBOX", "IMPORTANT", "Label_7"])
        self.assertEqual(m["internalDate"], ms(2026, 10, 25))
        self.assertIn("Thanks for applying to Acme", m["body"])
        # the thread link uses the decimal thread id, as Gmail's own links do
        self.assertTrue(m["url"].endswith(f"#all/thread-f:{int('18c0a0', 16)}"))
        self.assertIn("authuser=candidate@example.com", m["url"])

    def test_padding_optional(self):
        raw = make_mail("Hi", "Body")
        self.assertEqual(gm.from_api(api_message(raw, pad=True))["body"], gm.from_api(api_message(raw))["body"])

    def test_html_only(self):
        m = gm.from_api(api_message(make_mail(
            "Your application", None, html="<html><head><title>x</title><style>p{color:red}</style></head><body>"
            "<p>Dear&nbsp;Sam,</p><p>We regret to inform you that we will not be moving forward with your "
            "application for <b>Staff Engineer</b>.</p></body></html>", html_only=True)))
        self.assertIn("We regret to inform you", m["body"])
        self.assertIn("Staff Engineer", m["body"])
        self.assertNotIn("<p>", m["body"])
        self.assertNotIn("color:red", m["body"])
        self.assertNotIn("\xa0", m["body"])

    def test_stub_plain_part_falls_back_to_html(self):
        m = gm.from_api(api_message(make_mail("Interview", None, html="<div>We would like to invite you to an "
                                              "interview for the Backend Engineer role.</div>",
                                              stub="Please view this message in your browser.")))
        self.assertIn("Backend Engineer", m["body"])

    def test_unknown_stub_falls_back_to_html(self):
        m = gm.from_api(api_message(make_mail("Update", None, html="<div>Thank you for your application. After "
                                              "careful review we have decided not to move forward with your candidacy "
                                              "for the Data Engineer position at Initech. We appreciate your time.</div>",
                                              stub="Open in app")))
        self.assertIn("Data Engineer position at Initech", m["body"])

    def test_attachment_not_in_body(self):
        m = gm.from_api(api_message(make_mail("Offer letter", "We are pleased to offer you the role.",
                                              attach=b"%PDF-1.4 " + b"x" * 5000)))
        self.assertIn("pleased to offer", m["body"])
        self.assertNotIn("%PDF", m["body"])

    def test_non_ascii_and_unknown_charset(self):
        m = gm.from_api(api_message(make_mail("Votre candidature à Société Exemple – réponse",
                                              "Merci pour votre candidature. Café à Paris.", charset="iso-8859-1")))
        self.assertEqual(m["subject"], "Votre candidature à Société Exemple – réponse")
        self.assertIn("Café à Paris", m["body"])
        odd = make_mail("Odd", "We received your application.").replace(b'charset="utf-8"', b'charset="x-made-up"')
        self.assertIn("received your application", gm.from_api(api_message(odd))["body"])

    def test_missing_internal_date_uses_the_date_header(self):
        msg = api_message(make_mail("Hello", "Body", date="Mon, 02 Nov 2026 10:00:00 +0000"))
        del msg["internalDate"]
        self.assertEqual(gm.from_api(msg)["internalDate"], ms(2026, 11, 2, 10))

    def test_folded_subject_and_capped_body(self):
        raw = make_mail("Line one line two", "x" * (gm.MAX_BODY_CHARS + 5000)).replace(
            b"Subject: Line one line two", b"Subject: Line one\r\n   line two")
        m = gm.from_api(api_message(raw))
        self.assertEqual(m["subject"], "Line one line two")
        self.assertEqual(len(m["body"]), gm.MAX_BODY_CHARS)

    def test_no_thread_no_link(self):
        msg = api_message(make_mail("Hi", "Body"))
        msg["threadId"] = ""
        self.assertEqual(gm.from_api(msg)["url"], "")

    def test_html_to_text(self):
        out = gm.html_to_text("<html><head><title>t</title></head><body><script>x()</script>"
                              "<p>Hello&nbsp;there</p><p>Second&#8203; line</p><br>End</body></html>")
        self.assertEqual(out, "Hello there\n\nSecond line\n\nEnd")
        self.assertIn("text", gm.html_to_text("<p>text<div><b>unclosed"))


class Query(unittest.TestCase):
    def test_query_is_wellformed(self):
        q = gm.build_query("2026-10-20", "2026-11-02")
        self.assertIn("after:2026/10/19", q)           # a day early, for time zones
        self.assertIn("before:2026/11/03", q)          # a day late
        self.assertIn("-in:sent", q)
        self.assertIn("-in:drafts", q)
        self.assertIn('"next steps"', q)
        for word in ("referral", "referred", "application", "applied"):
            self.assertIn(word, q)

    def test_options(self):
        self.assertNotIn("(", gm.build_query("2026-10-20", everything=True))
        q = gm.build_query("2026-10-20", None, "foo OR bar")
        self.assertIn("(foo OR bar)", q)
        self.assertNotIn("before:", q)


class BrowserApi(unittest.TestCase):
    """tracker_api: JSON text in, JSON text out, as tracker-worker.js calls it."""

    def tearDown(self):
        jt.configure()

    def records(self):
        batch = {"account": "candidate@example.com", "messages": [
            api_message(make_mail("Thank you for applying to Acme", "We received your application for Backend "
                                  "Engineer at Acme.", "jobs@acme.example"), mid="a1", thread="a1", when=ms(2026, 10, 20)),
            api_message(make_mail("Acme interview", "Thanks for your application. We would like to schedule an "
                                  "interview with you for the Backend Engineer role.", "recruiter@acme.example"),
                        mid="a2", thread="a1",
                        when=ms(2026, 10, 24)),
            api_message(make_mail("Lunch", "See you at noon?", "friend@example.org"), mid="f1", when=ms(2026, 10, 25)),
            {"id": "bad", "threadId": "bad", "raw": None, "internalDate": "x"},
        ]}
        return json.loads(tracker_api.parse(json.dumps(batch)))

    def test_parse_skips_nothing_readable(self):
        out = self.records()
        self.assertEqual([m["id"] for m in out["messages"]], ["a1", "a2", "f1", "bad"])
        self.assertEqual(out["errors"], [])

    def test_parse_reports_a_broken_message_and_keeps_going(self):
        out = json.loads(tracker_api.parse(json.dumps({"messages": [{"id": "x", "raw": 5}, api_message(
            make_mail("Hi", "Body"))]})))
        self.assertEqual(len(out["messages"]), 1)
        self.assertTrue(out["errors"][0].startswith("x: "))

    def test_scan_groups_into_applications(self):
        msgs = self.records()["messages"]
        out = json.loads(tracker_api.scan(json.dumps({"messages": msgs, "since": "2026-10-01"})))
        self.assertEqual(out["notices"], 2)
        [app] = out["applications"]
        self.assertEqual((app["company"], app["position"], app["status"]), ("Acme", "Backend Engineer", "interviewing"))

    def test_scan_applies_settings(self):
        msgs = self.records()["messages"]
        out = json.loads(tracker_api.scan(json.dumps({"messages": msgs, "settings": {"ignore_senders": ["acme.example"]}})))
        self.assertEqual(out["applications"], [])

    def test_query(self):
        q = json.loads(tracker_api.query(json.dumps({"since": "2026-10-20", "before": "", "everything": True})))
        self.assertEqual(q, "after:2026/10/19 -in:sent -in:drafts")

    def test_prep_context_has_the_trail_and_the_emails_but_no_addresses(self):
        msgs = self.records()["messages"]
        apps = json.loads(tracker_api.scan(json.dumps({"messages": msgs})))["applications"]
        text = json.loads(tracker_api.prep_context(json.dumps({"applications": apps, "messages": msgs})))
        self.assertIn("## Applications at Acme (1)", text)
        self.assertIn("Backend Engineer: interviewing", text)
        self.assertIn("2026-10-24 interviewing: Acme interview", text)
        self.assertIn("schedule an interview", text)
        self.assertNotIn("See you at noon", text)          # another sender's mail
        self.assertNotIn("@", text)                         # sender addresses stay out
        self.assertEqual(json.loads(tracker_api.prep_context(json.dumps({"applications": []}))), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
