"""
gmail_message.py - turn a message from the Gmail API into the record job_tracker.py reads.

The Jobs page downloads each message with `users.messages.get?format=raw` (the full RFC 822
message, base64url encoded) and hands it to from_api() in the browser's Python (Pyodide). The
text extraction is the same as the old IMAP scraper's, so a message reads the same whichever
way it was downloaded.

Record fields:
  id            Gmail's message id (hex)
  threadId      Gmail's thread id (hex)
  internalDate  milliseconds since epoch, as Gmail received it
  from          sender address            subject   decoded subject
  labels        Gmail's label ids: INBOX, SENT, DRAFT, SPAM, TRASH, IMPORTANT, ...
  body          plain text (HTML is converted when there is no usable plain part)
  url           link that opens the thread in Gmail

Standard library only.
"""

from __future__ import annotations

import base64
import datetime as dt
import re
from email import message_from_bytes, policy
from email.utils import parseaddr, parsedate_to_datetime
from html.parser import HTMLParser

# Words that appear in nearly every application notice. Gmail does the matching on its side, so
# only plausible job mail is downloaded. "Download all mail in the range" skips this filter.
JOB_TERMS = [
    "application", "applications", "applied", "applying", "applicant", "candidate", "candidacy",
    "interview", "interviews", "interviewing", "assessment", "recruiter", "recruiting", "recruitment",
    "hiring", "offer", "regret", "referral", "referred", '"next steps"', '"your interest"', '"move forward"',
]
STUB_PLAIN = re.compile(
    r"view (?:this|the) (?:message|email|e-mail)|html (?:version|email|e-mail)|enable html|"
    r"(?:email|e-mail) client (?:does not|doesn't|cannot|can't)|best viewed in", re.I)
MAX_BODY_CHARS = 100_000


def parse_day(s: str) -> dt.datetime:
    return dt.datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc)


def build_query(since: str, before: str | None = None, terms: str | None = None,
                everything: bool = False) -> str:
    """Gmail search string. Starts a day early and ends a day late so time zones can't hide mail;
    the page applies the exact UTC cut-offs after download."""
    start = parse_day(since) - dt.timedelta(days=1)
    parts = [f"after:{start:%Y/%m/%d}"]
    if before:
        parts.append(f"before:{parse_day(before) + dt.timedelta(days=1):%Y/%m/%d}")
    parts += ["-in:sent", "-in:drafts"]
    if not everything:
        parts.append("(" + (terms or " OR ".join(JOB_TERMS)) + ")")
    return " ".join(parts)


# ------------------------------------------------------------------ message text

class _Text(HTMLParser):
    BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head", "title"):
            self.skip += 1
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head", "title"):
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, d):
        if not self.skip:
            self.out.append(d)


def html_to_text(s: str) -> str:
    p = _Text()
    try:
        p.feed(s)
        p.close()
    except Exception:  # malformed markup: keep whatever was read
        pass
    text = "".join(p.out)
    text = re.sub(r"[\u200b\u200c\u200d\u034f\u00ad\ufeff]", "", text).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def _part_text(part) -> str:
    try:
        return part.get_content()
    except (LookupError, UnicodeDecodeError, ValueError, AssertionError):
        payload = part.get_payload(decode=True) or b""
        for charset in (part.get_content_charset(), "utf-8"):
            try:
                return payload.decode(charset or "utf-8", "replace")
            except LookupError:
                continue
        return ""


def extract_body(msg) -> str:
    plain = html = ""
    for part in msg.walk():
        if part.is_multipart() or part.get_content_disposition() == "attachment":
            continue
        kind = part.get_content_type()
        if kind == "text/plain" and not plain:
            plain = _part_text(part)
        elif kind == "text/html" and not html:
            html = _part_text(part)
    # Some senders put a stub ("view this email in your browser") in the plain part and the real
    # text in HTML. Use the HTML when the plain part is empty, a known stub, or tiny next to it.
    plain = plain.strip()
    if html:
        converted = html_to_text(html)
        if (not plain or STUB_PLAIN.search(plain)
                or (len(plain) < 200 and len(converted) >= 2 * len(plain) + 40)):
            return converted[:MAX_BODY_CHARS]
    return plain[:MAX_BODY_CHARS]


# ------------------------------------------------------------------ Gmail API message -> record

def decode_raw(raw: str) -> bytes:
    """The API's `raw` field: base64url, possibly without padding."""
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))


def from_api(message: dict, account: str = "") -> dict:
    """One `users.messages.get?format=raw` response (id, threadId, labelIds, internalDate, raw)
    as a record. `account` is the mailbox's address, for the link that opens the thread."""
    msg = message_from_bytes(decode_raw(message.get("raw") or ""), policy=policy.default)
    try:
        ts = int(message.get("internalDate"))
    except (TypeError, ValueError):
        try:
            ts = int(parsedate_to_datetime(str(msg.get("Date"))).timestamp() * 1000)
        except (TypeError, ValueError):
            ts = 0
    thread = str(message.get("threadId") or "")
    try:
        thread_dec = str(int(thread, 16)) if thread else ""
    except ValueError:
        thread_dec = ""
    return {
        "id": str(message.get("id") or ""),
        "threadId": thread,
        "internalDate": ts,
        "from": parseaddr(str(msg.get("From") or ""))[1],
        "subject": " ".join(str(msg.get("Subject") or "").split()),
        "labels": [str(x) for x in message.get("labelIds") or []],
        "body": extract_body(msg),
        "url": (f"https://mail.google.com/mail/?authuser={account}#all/thread-f:{thread_dec}"
                if thread_dec else ""),
    }
