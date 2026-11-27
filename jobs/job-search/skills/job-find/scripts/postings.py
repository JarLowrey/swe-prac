#!/usr/bin/env python3
"""Recent job postings found by the job-find skill.

Keeps postings.json in the job-search folder: JOB_SEARCH_DIR if set, otherwise the current
directory if it has a reference/profile.yaml, otherwise the repo this script lives in, otherwise
~/job-search. The agent reads LinkedIn and Indeed search results in the browser and writes what it
saw as a batch file; this script turns batches into clean records (dates, pay, workplace,
canonical links), merges them without duplicates and lists them. The site's Job finder page
imports postings.json and charts it. Standard library only.

Try it on the sample data: JOB_SEARCH_DIR=examples python postings.py list --days 14

Usage:
  postings.py urls --query Q [--location L] [--days 1|3|7|14] [--remote] [--source both|linkedin|indeed] [--page N]
  postings.py add  BATCH.json [BATCH.json ...]       (- reads a batch from stdin)
  postings.py list [--days N] [--source S] [--limit N]

A batch is one search's results, or a JSON list of them:
  {"source": "linkedin", "query": "backend engineer", "location": "Denver, CO", "remote": false,
   "days": 1, "url": "<search url>", "ran_at": "2026-11-27T15:04:05Z", "note": "",
   "postings": [{"id": "4012345678", "url": "...", "title": "...", "company": "...",
                 "location": "Denver, CO (Hybrid)", "posted_text": "2 days ago",
                 "salary_text": "$150K/yr - $190K/yr", "easy_apply": true}]}
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

VERSION = 1
SOURCES = ("linkedin", "indeed")
DAYS = (1, 3, 7, 14)
MAX_SEARCHES = 200
PAGE_SIZE = {"linkedin": 25, "indeed": 10}
POSTING_KEYS = (
    "id", "source", "url", "title", "company", "location", "workplace", "posted", "posted_text",
    "salary_text", "salary_min", "salary_max", "easy_apply", "query", "first_seen", "last_seen", "also_on",
)
SEARCH_KEYS = ("source", "query", "location", "remote", "days", "url", "ran_at", "found", "note")
# Query parameters that only record where a click came from.
TRACKING_PARAMS = {"trk", "trackingid", "refid", "ref", "referrer", "src", "source", "from", "tk", "vjs", "eid"}


# ---------------------------------------------------------------- where the data lives

def data_dir() -> Path:
    env = os.environ.get("JOB_SEARCH_DIR")
    if env:
        return Path(env).expanduser()
    candidates = [Path.cwd()]
    # Kit layout: <kit>/skills/job-find/scripts/postings.py.
    # resolve() follows a junction or symlink from an agent's personal skills folder.
    here = Path(__file__).resolve()
    if len(here.parents) > 3:
        candidates.append(here.parents[3])
    for folder in candidates:
        if (folder / "reference" / "profile.yaml").exists():
            return folder
    return Path.home() / "job-search"


def postings_path() -> Path:
    return data_dir() / "postings.json"


def now_iso() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------- search URLs

def search_url(source: str, query: str, location: str = "", days: int = 1, remote: bool = False, page: int = 0) -> str:
    """The results page for one search, newest first, limited to postings from the last `days` days."""
    if source not in SOURCES:
        raise ValueError(f"source must be one of {', '.join(SOURCES)}")
    if days not in DAYS:
        raise ValueError(f"days must be one of {', '.join(map(str, DAYS))}")
    query = " ".join(query.split())
    location = " ".join((location or "").split())
    if source == "linkedin":
        params = [("keywords", query)]
        if location:
            params.append(("location", location))
        params += [("f_TPR", f"r{days * 86400}"), ("sortBy", "DD")]
        if remote:
            params.append(("f_WT", "2"))
        if page:
            params.append(("start", str(page * PAGE_SIZE[source])))
        base = "https://www.linkedin.com/jobs/search/"
    else:
        # Indeed has no separate remote switch that's stable; "Remote" as the place is.
        params = [("q", query), ("l", "Remote" if remote else location), ("fromage", str(days)), ("sort", "date")]
        if page:
            params.append(("start", str(page * PAGE_SIZE[source])))
        base = "https://www.indeed.com/jobs"
    return f"{base}?{urlencode(params, quote_via=quote)}"


def search_urls(query: str, location: str = "", days: int = 1, remote: bool = False, source: str = "both",
                page: int = 0) -> list[dict]:
    sources = SOURCES if source == "both" else (source,)
    return [{"source": s, "query": " ".join(query.split()), "location": " ".join((location or "").split()),
             "remote": remote, "days": days, "url": search_url(s, query, location, days, remote, page)}
            for s in sources]


# ---------------------------------------------------------------- cleaning one posting

def clean(text) -> str:
    return " ".join(str(text or "").split())


def parse_date(value: str) -> dt.date:
    """The calendar date of an ISO timestamp ("2026-11-27T15:04:05Z") or date."""
    value = clean(value)
    if not value:
        return dt.datetime.now(dt.UTC).date()
    try:
        return dt.datetime.fromisoformat(value).date()  # 3.11+ reads a trailing Z
    except ValueError:
        return dt.date.fromisoformat(value[:10])


_AGO = re.compile(r"(\d+)\s*\+?\s*(minute|min|hour|hr|day|week|wk|month|mo)s?\b", re.IGNORECASE)
_TODAY = re.compile(r"\b(just posted|today|just now|new)\b", re.IGNORECASE)


def parse_posted(text: str, on: dt.date) -> str:
    """posted_text as shown on the card ("2 days ago", "Just posted", "30+ days ago") -> YYYY-MM-DD."""
    text = clean(text)
    if not text:
        return ""
    m = _AGO.search(text)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        days = 0 if unit in ("minute", "min", "hour", "hr") else n * {"day": 1, "week": 7, "wk": 7}.get(unit, 30)
        return (on - dt.timedelta(days=days)).isoformat()
    if re.search(r"\byesterday\b", text, re.IGNORECASE):
        return (on - dt.timedelta(days=1)).isoformat()
    if _TODAY.search(text):
        return on.isoformat()
    return ""


_PERIODS = (
    (re.compile(r"\b(hour|hourly|hr)\b|/\s*h\b", re.IGNORECASE), 2080),
    (re.compile(r"\b(day|daily)\b|/\s*d\b", re.IGNORECASE), 260),
    (re.compile(r"\b(week|weekly|wk)\b", re.IGNORECASE), 52),
    (re.compile(r"\b(month|monthly|mo)\b", re.IGNORECASE), 12),
    (re.compile(r"\b(year|yearly|annual|annually|yr)\b", re.IGNORECASE), 1),
)
_AMOUNT = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*([kKmM])?(?![\w])")


def parse_salary(text: str) -> tuple[int | None, int | None]:
    """Pay as shown -> (min, max) in US dollars a year, or (None, None) if it isn't clearly USD."""
    text = clean(text)
    if "$" not in text or re.search(r"(?<![A-Za-z])(?!US\$)[A-Za-z]{1,3}\$|[€£¥₹]", text):
        return None, None
    amounts = []
    for m in _AMOUNT.finditer(text[text.index("$"):]):
        value = float(m.group(1).replace(",", ""))
        suffix = (m.group(2) or "").lower()
        value *= 1000 if suffix == "k" else 1_000_000 if suffix == "m" else 1
        amounts.append(value)
        if len(amounts) == 2:
            break
    if not amounts:
        return None, None
    per = next((mult for rx, mult in _PERIODS if rx.search(text)), None)
    if per is None:
        per = 2080 if max(amounts) < 500 else 1  # "$45 - $60" with no period is an hourly rate
    low, high = min(amounts) * per, max(amounts) * per
    if high < 15_000 or high > 5_000_000:  # not a plausible yearly pay
        return None, None
    return round(low), round(high)


_WORKPLACE = (
    (re.compile(r"\(\s*remote\s*\)", re.IGNORECASE), "remote"),
    (re.compile(r"\(\s*hybrid\s*\)", re.IGNORECASE), "hybrid"),
    (re.compile(r"\(\s*on[- ]?site\s*\)", re.IGNORECASE), "onsite"),
)


def parse_workplace(location: str, title: str = "") -> tuple[str, str]:
    """Location as shown -> (workplace, location without the workplace marker)."""
    loc = clean(location)
    for rx, kind in _WORKPLACE:
        if rx.search(loc):
            return kind, clean(rx.sub("", loc)).strip(" ,·-")
    m = re.match(r"^(hybrid(?: work| remote)?|remote|on[- ]?site)\s+in\s+(.+)$", loc, re.IGNORECASE)
    if m:
        word = m.group(1).lower()
        return ("hybrid" if word.startswith("hybrid") else "remote" if word == "remote" else "onsite"), clean(m.group(2))
    if re.fullmatch(r"(fully\s+)?remote", loc, re.IGNORECASE):
        return "remote", ""
    if re.fullmatch(r"hybrid( remote)?", loc, re.IGNORECASE):
        return "hybrid", ""
    if re.search(r"\bremote\b", loc, re.IGNORECASE):
        return "remote", clean(re.sub(r"\bremote\b", "", loc, flags=re.IGNORECASE)).strip(" ,·-()")
    if re.search(r"\bhybrid\b", loc, re.IGNORECASE):
        return "hybrid", clean(re.sub(r"\bhybrid\b", "", loc, flags=re.IGNORECASE)).strip(" ,·-()")
    t = clean(title)
    if re.search(r"\bhybrid\b", t, re.IGNORECASE):
        return "hybrid", loc
    if re.search(r"\bremote\b", t, re.IGNORECASE):
        return "remote", loc
    return "", loc


def source_id(source: str, raw_id: str, url: str) -> str:
    """The job's id on its source, from the id given or, failing that, the URL."""
    raw = clean(raw_id)
    if raw and ":" in raw and raw.split(":", 1)[0] in SOURCES:
        raw = raw.split(":", 1)[1]
    if raw:
        return raw
    url = clean(url)
    if source == "linkedin":
        m = (re.search(r"/jobs/view/(?:[^/?#]*-)?(\d+)(?=[/?#]|$)", url)
             or re.search(r"[?&]currentJobId=(\d+)", url) or re.search(r"jobPosting:(\d+)", url))
    else:
        m = re.search(r"[?&]jk=([0-9a-fA-F]+)", url)
    return m.group(1) if m else ""


def canonical_url(source: str, sid: str, url: str) -> str:
    """LinkedIn and Indeed links become their plain job page; other https links lose tracking params."""
    url = clean(url)
    host = urlsplit(url).hostname or "" if url else ""
    on_source = host == f"{source}.com" or host.endswith(f".{source}.com")
    if not url or on_source:
        if not sid:
            return ""
        return (f"https://www.linkedin.com/jobs/view/{sid}/" if source == "linkedin"
                else f"https://www.indeed.com/viewjob?jk={sid}")
    parts = urlsplit(url)
    if parts.scheme != "https":
        return canonical_url(source, sid, "")
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")]
    return urlunsplit(("https", parts.netloc, parts.path, urlencode(query), ""))


def normalize(source: str, raw: dict, on: dt.date, query: str) -> dict | None:
    """One card as the agent read it -> a postings.json record, or None if it has no id or title."""
    sid = source_id(source, raw.get("id", ""), raw.get("url", ""))
    title = clean(raw.get("title"))
    if not sid or not title:
        return None
    workplace, location = parse_workplace(raw.get("location", ""), title)
    salary_text = clean(raw.get("salary_text"))
    low, high = parse_salary(salary_text)
    posted_text = clean(raw.get("posted_text"))
    easy = raw.get("easy_apply")
    return {
        "id": f"{source}:{sid}",
        "source": source,
        "url": canonical_url(source, sid, raw.get("url", "")),
        "title": title,
        "company": clean(raw.get("company")),
        "location": location,
        "workplace": workplace,
        "posted": parse_posted(posted_text, on),
        "posted_text": posted_text,
        "salary_text": salary_text,
        "salary_min": low,
        "salary_max": high,
        "easy_apply": True if easy is True or str(easy).lower() in ("true", "yes", "1") else None,
        "query": clean(raw.get("query")) or query,
        "first_seen": on.isoformat(),
        "last_seen": on.isoformat(),
        "also_on": [],
    }


# ---------------------------------------------------------------- matching and merging

_SUFFIXES = {"inc", "llc", "ltd", "corp", "corporation", "co", "company", "plc", "gmbh", "lp", "llp", "limited", "incorporated"}
_WORDS = {"sr": "senior", "jr": "junior", "eng": "engineer", "swe": "software engineer", "mgr": "manager"}


def _words(text: str) -> list[str]:
    return re.sub(r"[^\w\s]", " ", clean(text).casefold().replace("&", " and ")).split()


def norm_company(name: str) -> str:
    words = _words(name)
    while words and words[-1] in _SUFFIXES:
        words.pop()
    return " ".join(words)


def norm_title(title: str) -> str:
    return " ".join(_WORDS.get(w, w) for w in _words(title))


def match_key(p: dict) -> tuple[str, str, str]:
    place = "remote" if p.get("workplace") == "remote" else " ".join(_words(p.get("location", "")))
    return norm_company(p.get("company", "")), norm_title(p.get("title", "")), place


def empty() -> dict:
    return {"version": VERSION, "updated_at": "", "searches": [], "postings": []}


def load(path: Path) -> dict:
    if not path.exists():
        return empty()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != VERSION:
        raise SystemExit(f"{path} isn't a version {VERSION} postings file.")
    data.setdefault("searches", [])
    data.setdefault("postings", [])
    return data


def save(data: dict, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _fill(existing: dict, new: dict) -> None:
    """Keep what's known; take anything the existing record is missing."""
    for k in ("url", "title", "company", "location", "workplace", "posted", "posted_text", "salary_text", "query"):
        if not existing.get(k) and new.get(k):
            existing[k] = new[k]
    if existing.get("salary_min") is None and new.get("salary_min") is not None:
        existing["salary_min"], existing["salary_max"] = new["salary_min"], new["salary_max"]
    if existing.get("easy_apply") is None and new.get("easy_apply"):
        existing["easy_apply"] = True
    existing["last_seen"] = max(existing.get("last_seen") or "", new["last_seen"])
    existing["first_seen"] = min(existing.get("first_seen") or new["first_seen"], new["first_seen"])


def sort_postings(postings: list[dict]) -> list[dict]:
    postings.sort(key=lambda p: (p.get("posted") or "", p.get("first_seen") or "", p["id"]), reverse=True)
    return postings


def add_batch(data: dict, batch: dict, now: str | None = None) -> dict:
    """Merge one search's results into `data`. Returns counts: found, new, seen, also_on, skipped."""
    source = clean(batch.get("source")).lower()
    if source not in SOURCES:
        raise ValueError(f"batch source must be one of {', '.join(SOURCES)}, not {batch.get('source')!r}")
    now = now or now_iso()
    ran_at = clean(batch.get("ran_at")) or now
    on = parse_date(ran_at)
    query = clean(batch.get("query"))
    by_id: dict[str, dict] = {}
    by_key: dict[tuple, dict] = {}
    for p in data["postings"]:
        for pid in (p["id"], *p.get("also_on", [])):
            by_id[pid] = p
        by_key.setdefault(match_key(p), p)
    counts = {"found": 0, "new": 0, "seen": 0, "also_on": 0, "skipped": 0}
    for raw in batch.get("postings") or []:
        counts["found"] += 1
        rec = normalize(source, raw if isinstance(raw, dict) else {}, on, query)
        if rec is None:
            counts["skipped"] += 1
            continue
        same = by_id.get(rec["id"])
        if same is not None:
            _fill(same, rec)
            counts["seen"] += 1
            continue
        twin = by_key.get(match_key(rec))
        if twin is not None and twin["source"] != source and rec["company"]:
            twin.setdefault("also_on", []).append(rec["id"])
            _fill(twin, rec)
            by_id[rec["id"]] = twin
            counts["also_on"] += 1
            continue
        data["postings"].append(rec)
        by_id[rec["id"]] = rec
        by_key.setdefault(match_key(rec), rec)
        counts["new"] += 1
    search_link = clean(batch.get("url"))
    data["searches"].insert(0, {
        "source": source, "query": query, "location": clean(batch.get("location")),
        "remote": bool(batch.get("remote")), "days": int(batch.get("days") or 0),
        "url": search_link if search_link.startswith("https://") else "",
        "ran_at": ran_at, "found": counts["found"], "note": clean(batch.get("note")),
    })
    del data["searches"][MAX_SEARCHES:]
    sort_postings(data["postings"])
    data["version"] = VERSION
    data["updated_at"] = now
    return counts


def read_batches(paths: list[str]) -> list[dict]:
    batches: list[dict] = []
    for p in paths:
        text = sys.stdin.read() if p == "-" else Path(p).read_text(encoding="utf-8")
        loaded = json.loads(text)
        batches.extend(loaded if isinstance(loaded, list) else [loaded])
    return batches


# ---------------------------------------------------------------- listing

def recent(data: dict, days: int | None = None, source: str | None = None, today: dt.date | None = None) -> list[dict]:
    today = today or dt.date.today()
    cutoff = (today - dt.timedelta(days=days)).isoformat() if days else ""
    return [p for p in data["postings"]
            if (not source or p["source"] == source) and (p.get("posted") or p.get("first_seen") or "") >= cutoff]


def money(p: dict) -> str:
    lo, hi = p.get("salary_min"), p.get("salary_max")
    if lo is None:
        return ""
    k = lambda v: f"${round(v / 1000)}K"
    return k(lo) if lo == hi else f"{k(lo)}-{k(hi)}"


def table(postings: list[dict]) -> str:
    rows = [("Posted", "Source", "Company", "Title", "Where", "Pay")]
    for p in postings:
        where = ", ".join(x for x in (p.get("location"), p.get("workplace")) if x)
        source = p["source"] + (" +" if p.get("also_on") else "")
        rows.append((p.get("posted") or "?", source, p.get("company", ""), p["title"], where, money(p)))
    widths = [min(max(len(r[i]) for r in rows), cap) for i, cap in enumerate((10, 10, 24, 44, 30, 12))]
    cut = lambda s, w: s if len(s) <= w else s[: w - 1] + "…"
    return "\n".join("  ".join(cut(c, w).ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows)


# ---------------------------------------------------------------- command line

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--file", type=Path, help="postings file (default: postings.json in the job-search folder)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    u = sub.add_parser("urls", help="print the search URLs for one query and place, as JSON")
    u.add_argument("--query", required=True)
    u.add_argument("--location", default="")
    u.add_argument("--days", type=int, default=1, choices=DAYS)
    u.add_argument("--remote", action="store_true")
    u.add_argument("--source", default="both", choices=("both", *SOURCES))
    u.add_argument("--page", type=int, default=0, help="0 for the first results page, 1 for the second")

    a = sub.add_parser("add", help="merge batch files into postings.json")
    a.add_argument("batches", nargs="+", help="batch JSON files, or - for stdin")

    li = sub.add_parser("list", help="show recent postings")
    li.add_argument("--days", type=int, help="only postings from the last N days")
    li.add_argument("--source", choices=SOURCES)
    li.add_argument("--limit", type=int, default=100)

    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # a company name the console can't show
    path = args.file or postings_path()

    if args.cmd == "urls":
        print(json.dumps(search_urls(args.query, args.location, args.days, args.remote, args.source, args.page), indent=2))
        return 0

    if args.cmd == "add":
        data = load(path)
        for batch in read_batches(args.batches):
            c = add_batch(data, batch)
            where = "remote" if batch.get("remote") else clean(batch.get("location")) or "anywhere"
            print(f"{batch.get('source')} \"{clean(batch.get('query'))}\" {where}: {c['found']} found, {c['new']} new, "
                  f"{c['seen']} already seen, {c['also_on']} also on the other site, {c['skipped']} skipped")
        save(data, path)
        print(f"{len(data['postings'])} postings in {path}")
        return 0

    data = load(path)
    shown = recent(data, args.days, args.source)
    print(table(shown[: args.limit]) if shown else "No postings.")
    if len(shown) > args.limit:
        print(f"... and {len(shown) - args.limit} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
