"""
tracker_api.py - what the Jobs page calls in the browser's Python (tracker-worker.js).

Every function takes and returns JSON text, so only strings cross between JavaScript and Python.

  query(args)          the Gmail search for a date range
  parse(batch)         Gmail API messages (format=raw) -> records (gmail_message.from_api)
  scan(payload)        records -> applications (job_tracker.scan_messages), with your settings
  prep_context(args)   one company's applications and emails, as text for an interview-prep prompt
"""

from __future__ import annotations

import json
import re

import gmail_message
import job_tracker as jt

PREP_BODY_CHARS = 3500
PREP_MAX_EMAILS = 8


def query(args: str) -> str:
    a = json.loads(args)
    return json.dumps(gmail_message.build_query(a["since"], a.get("before") or None,
                                                a.get("terms") or None, bool(a.get("everything"))))


def parse(batch: str) -> str:
    """{"account": str, "messages": [api message, ...]} -> {"messages": [record], "errors": [str]}.
    A message that can't be read is reported and skipped, so one bad message doesn't stop a sync."""
    b = json.loads(batch)
    out, errors = [], []
    for m in b.get("messages", []):
        try:
            out.append(gmail_message.from_api(m, b.get("account") or ""))
        except Exception as e:  # noqa: BLE001 - any parse failure skips just that message
            errors.append(f"{m.get('id')}: {type(e).__name__}: {e}")
    return json.dumps({"messages": out, "errors": errors}, ensure_ascii=False)


def scan(payload: str) -> str:
    """{"messages", "since", "before", "settings": {"vendor_domains", "ignore_senders"}} ->
    {"applications": [...], "notices": number of messages kept as application notices}."""
    p = json.loads(payload)
    s = p.get("settings") or {}
    jt.configure(s.get("vendor_domains") or (), s.get("ignore_senders") or ())
    notices, apps = jt.scan_messages(p.get("messages") or [], p.get("since") or None, p.get("before") or None)
    return json.dumps({"applications": apps, "notices": sum(1 for n in notices if n["job"])},
                      ensure_ascii=False)


def _squash(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def _clean(body: str) -> str:
    text = jt.clean_body(body)
    return text if len(text) <= PREP_BODY_CHARS else text[:PREP_BODY_CHARS] + " [...]"


def prep_context(args: str) -> str:
    """{"applications": [one company's applications], "messages": [records]} -> markdown.

    The applications with the notices that set each status, then that company's emails, newest
    first, cleaned and trimmed: the notices themselves plus any other email whose subject or
    sender names the company."""
    a = json.loads(args)
    apps, msgs = a.get("applications") or [], a.get("messages") or []
    if not apps:
        return json.dumps("")
    lines = [f"## Applications at {apps[0].get('company')} ({len(apps)})"]
    ids = set()
    for x in apps:
        item = f" ({x['item']})" if x.get("item") else ""
        lines.append(f"\n- {x.get('position') or 'Position not stated'}: {x.get('status')}{item}, "
                     f"first email {x.get('first_date')}, latest {x.get('last_date')}")
        for n in x.get("notices") or []:
            ids.add(n.get("id"))
            lines.append(f"  - {n.get('date')} {n.get('status')}: {n.get('subject', '')}")
    names = {n for n in {_squash(x.get("company")) for x in apps} if len(n) >= 4}
    picked = [m for m in msgs if m.get("id") in ids
              or any(n in _squash(m.get("subject")) or n in _squash(m.get("from")) for n in names)]
    picked.sort(key=lambda m: int(m.get("internalDate") or 0), reverse=True)
    shown = picked[:PREP_MAX_EMAILS]
    lines.append(f"\n## Emails ({len(picked)} found, the newest {len(shown)} shown)")
    for m in shown:
        lines.append(f"\n### {jt.iso(int(m.get('internalDate') or 0))} | {m.get('subject', '')}")
        lines.append(_clean(m.get("body", "")))
    return json.dumps("\n".join(lines), ensure_ascii=False)
