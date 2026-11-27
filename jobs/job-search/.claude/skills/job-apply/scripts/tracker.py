#!/usr/bin/env python3
"""Job application tracker used by the job-apply skill.

Keeps one row per application in tracker.csv inside the job-search folder:
JOB_SEARCH_DIR if set, otherwise the current directory if it has a
reference/profile.yaml, otherwise the repo this script lives in, otherwise
~/job-search.
Standard library only. The CSV opens cleanly in Excel or Google Sheets.

Try it on the fake data: JOB_SEARCH_DIR=examples python tracker.py list

Usage:
  tracker.py find   [--url URL] [--company NAME]
  tracker.py add    --company C --role R --url U [--location L] [--ats A]
                    [--status S] [--folder F] [--note N] [--force]
  tracker.py update ID [--status S] [--note N] [--folder F] [--location L] [--ats A]
  tracker.py list   [--status S]

Suggested statuses: ready-for-review, submitted, skipped-location, skipped,
interviewing, rejected, offer, withdrawn.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

FIELDS = [
    "id", "date_added", "company", "role", "location", "url", "ats",
    "status", "date_updated", "folder", "notes",
]

# Query parameters that only record where a click came from. Dropped when
# comparing URLs so the same job found via two sources is recognized.
TRACKING_PARAMS = {
    "gh_src", "source", "src", "ref", "referrer", "lever-source",
    "lever-origin", "trk", "trackingid", "refid",
}


def data_dir() -> Path:
    env = os.environ.get("JOB_SEARCH_DIR")
    if env:
        return Path(env).expanduser()
    candidates = [Path.cwd()]
    # Repo layout: <repo>/.claude/skills/job-apply/scripts/tracker.py.
    # resolve() follows a junction or symlink from ~/.claude/skills.
    here = Path(__file__).resolve()
    if len(here.parents) > 4:
        candidates.append(here.parents[4])
    for folder in candidates:
        if (folder / "reference" / "profile.yaml").exists():
            return folder
    return Path.home() / "job-search"


def tracker_path() -> Path:
    return data_dir() / "tracker.csv"


def today() -> str:
    return dt.date.today().isoformat()


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    parts = urlsplit(url)
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")
    ]
    path = parts.path.rstrip("/")
    for suffix in ("/apply", "/application"):
        if path.lower().endswith(suffix):
            path = path[: -len(suffix)]
    host = parts.netloc.lower().removeprefix("www.")
    if host.endswith("greenhouse.io"):
        host = "greenhouse.io"  # boards. and job-boards. serve the same postings
    return urlunsplit(("https", host, path, urlencode(query), "")).lower()


def load() -> list[dict]:
    path = tracker_path()
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [{k: (row.get(k) or "") for k in FIELDS} for row in csv.DictReader(f)]


def save(rows: list[dict]) -> None:
    path = tracker_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    # utf-8-sig so Excel shows non-ASCII characters correctly.
    with tmp.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    try:
        os.replace(tmp, path)
    except PermissionError:
        tmp.unlink(missing_ok=True)
        sys.exit(f"Could not write {path}. It is probably open in Excel; close it and run the command again.")


def show(rows: list[dict]) -> None:
    if not rows:
        print("No matching applications.")
        return
    for r in rows:
        print(f"#{r['id']}  {r['status'] or '-':<17} {r['company']} | {r['role']} | {r['location'] or '?'}")
        print(f"      added {r['date_added']}, updated {r['date_updated'] or '-'}  {r['url']}")
        if r["folder"]:
            print(f"      folder: {r['folder']}")
        if r["notes"]:
            print(f"      notes: {r['notes']}")


def find_rows(rows: list[dict], url: str | None = None, company: str | None = None) -> list[dict]:
    target = normalize_url(url) if url else None
    name = company.strip().lower() if company else None
    return [
        r for r in rows
        if (target and normalize_url(r["url"]) == target)
        or (name and name in r["company"].lower())
    ]


def append_note(existing: str, note: str) -> str:
    entry = f"{today()}: {note.strip()}"
    return f"{existing} | {entry}" if existing else entry


def cmd_find(args) -> int:
    if not (args.url or args.company):
        sys.exit("find needs --url or --company")
    show(find_rows(load(), url=args.url, company=args.company))
    return 0


def cmd_add(args) -> int:
    rows = load()
    dupes = find_rows(rows, url=args.url)
    if dupes and not args.force:
        print("Already tracked (pass --force to add another row anyway):")
        show(dupes)
        return 2
    next_id = max((int(r["id"]) for r in rows if r["id"].isdigit()), default=0) + 1
    row = {
        "id": str(next_id),
        "date_added": today(),
        "company": args.company,
        "role": args.role,
        "location": args.location or "",
        "url": args.url,
        "ats": args.ats or "",
        "status": args.status,
        "date_updated": today(),
        "folder": args.folder or "",
        "notes": append_note("", args.note) if args.note else "",
    }
    rows.append(row)
    save(rows)
    print(f"Added #{next_id}")
    show([row])
    return 0


def cmd_update(args) -> int:
    rows = load()
    match = [r for r in rows if r["id"] == str(args.id)]
    if not match:
        sys.exit(f"No application with id {args.id}. Run `list` or `find` to see ids.")
    row = match[0]
    for field in ("status", "folder", "location", "ats"):
        value = getattr(args, field)
        if value:
            row[field] = value
    if args.note:
        row["notes"] = append_note(row["notes"], args.note)
    row["date_updated"] = today()
    save(rows)
    show([row])
    return 0


def cmd_list(args) -> int:
    rows = load()
    if args.status:
        rows = [r for r in rows if r["status"].lower() == args.status.lower()]
    show(rows)
    if rows:
        counts: dict[str, int] = {}
        for r in rows:
            counts[r["status"] or "-"] = counts.get(r["status"] or "-", 0) + 1
        print("\n" + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    return 0


def main() -> int:
    # The Windows console defaults to a legacy code page when output is piped.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Job application tracker")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("find", help="look up applications by URL or company")
    p.add_argument("--url")
    p.add_argument("--company")
    p.set_defaults(func=cmd_find)

    p = sub.add_parser("add", help="add an application")
    p.add_argument("--company", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--location")
    p.add_argument("--ats", help="Greenhouse, Lever, Ashby, Workday, ...")
    p.add_argument("--status", default="ready-for-review")
    p.add_argument("--folder")
    p.add_argument("--note")
    p.add_argument("--force", action="store_true", help="add even if the URL is already tracked")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("update", help="change status or add a note")
    p.add_argument("id", type=int)
    p.add_argument("--status")
    p.add_argument("--note", help="appended with today's date")
    p.add_argument("--folder")
    p.add_argument("--location")
    p.add_argument("--ats")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("list", help="list applications")
    p.add_argument("--status")
    p.set_defaults(func=cmd_list)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
