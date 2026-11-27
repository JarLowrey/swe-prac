---
name: job-find
description: Search LinkedIn and Indeed in the user's own browser for recently posted jobs that match their profile (target roles and acceptable locations), save every posting to postings.json with its date, pay, workplace and link, and summarize what's new. Use this whenever the user runs /job-find, or asks to find jobs, search LinkedIn or Indeed, see recent or new postings, or check what's been posted this week, including with their own keywords, places or date range.
---

# Job find

Searches LinkedIn and Indeed for jobs posted recently, reading only the search results pages, and keeps what it finds in `postings.json` in the **job-search folder**: `$JOB_SEARCH_DIR` if set, otherwise the current directory if it contains `reference/profile.yaml`, otherwise `~/job-search`. The site's **Jobs > Job finder** page imports that file and charts it.

This skill only looks. It never applies, saves a job, sets an alert or messages anyone: those are the user's actions, under their name. To apply to something it finds, the user hands the link to the `job-apply` skill.

Run the script by its absolute path so it works from any shell: `python <this skill's directory>/scripts/postings.py <urls|add|list> ...` (add `--help` for options). It finds the job-search folder the same way.

## 1. Plan the searches

Read `reference/profile.yaml`. If it's missing, the user can still give keywords and places in the prompt; otherwise tell them to set up the profile (see the job-search README) and stop.

- **Keywords:** 1 to 3 short phrases built from `preferences.target_roles`, the way a job board matches them: 2 to 4 words, no "or" and no slashes. "Senior or staff backend / infrastructure software engineer" becomes `senior backend engineer` and `senior infrastructure engineer`. Leave out seniority words if the target roles don't name a level.
- **Places:** one search per entry in `location.acceptable_locations`. An area ("Denver area, onsite or hybrid (Denver, Boulder, ...)") searches its main city with the state, `Denver, CO`; the job board's own radius covers the suburbs. A remote entry ("Remote within the US") is a remote search with the location `United States`.
- **Posted within:** 1 day unless the user says otherwise; the script accepts 1, 3, 7 or 14.
- **Sources:** both LinkedIn and Indeed unless the user names one.

Anything the user says in the prompt (keywords, places, days, sources) replaces what the profile suggests. Each keyword and place pair is one search per source. Keep to **at most 6 results-page loads per source** in a run, counting second pages; if the plan needs more, run the first 6 and list the rest for next time.

Get each pair's URLs from the script, so the filters are right:

```
python <skill dir>/scripts/postings.py urls --query "senior backend engineer" --location "Denver, CO" --days 1
python <skill dir>/scripts/postings.py urls --query "senior backend engineer" --location "United States" --remote --days 1
```

It prints a JSON list with one entry per source (`--source linkedin` or `--source indeed` for one), each with the search `url`. `--page 1` gives the second results page.

## 2. Read each results page

Use your browser tools on the user's own signed-in Chrome: open a URL, read the page text, read its links, and run JavaScript in the page if your tools can. Work in one new tab and leave the user's other tabs alone.

Open the search URL and wait for the results to load. On LinkedIn, the list loads as it scrolls: scroll the results list to the bottom two or three times, a second apart, before collecting. Then collect the cards. Try JavaScript first:

**LinkedIn** (signed in or not):

```js
(() => {
  const seen = new Map();
  for (const a of document.querySelectorAll('a[href*="/jobs/view/"]')) {
    const m = a.href.match(/\/jobs\/view\/(?:[^/?#]*-)?(\d+)(?=[/?#]|$)/);
    if (!m || seen.has(m[1])) continue;
    const card = a.closest('li') || a.parentElement;
    seen.set(m[1], { id: m[1], url: a.href,
      lines: (card.innerText || '').split('\n').map(s => s.trim()).filter(Boolean) });
  }
  return JSON.stringify([...seen.values()]);
})()
```

**Indeed:**

```js
(() => {
  const seen = new Map();
  for (const el of document.querySelectorAll('[data-jk]')) {
    const id = el.getAttribute('data-jk');
    if (!id || seen.has(id)) continue;
    const card = el.closest('.job_seen_beacon, .cardOutline, li') || el;
    seen.set(id, { id, lines: (card.innerText || '').split('\n').map(s => s.trim()).filter(Boolean) });
  }
  return JSON.stringify([...seen.values()]);
})()
```

If you can't run JavaScript, or it returns nothing, read the page's links and text instead: LinkedIn job links contain `/jobs/view/<id>`, Indeed's contain `jk=<id>`, and each card's text sits around its link.

Turn each card's lines into one posting, taking text **as shown**:

| Field | From the card |
|---|---|
| `id` | the number from `/jobs/view/<id>` (LinkedIn) or the `jk` value (Indeed) |
| `url` | the job link if you have it; the script rebuilds a clean one from the id anyway |
| `title` | the job title (LinkedIn often repeats it on the next line; take it once) |
| `company` | the company name |
| `location` | the place line, with any "(Remote)", "(Hybrid)", "Hybrid work in ..." left in; the script reads the workplace from it |
| `posted_text` | "2 days ago", "Just posted", "30+ days ago", "Posted 3 days ago"; empty if the card shows no date |
| `salary_text` | the pay line ("$150K/yr - $190K/yr", "$60 - $75 an hour"), or empty |
| `easy_apply` | `true` if the card says "Easy Apply" (LinkedIn) or "Easily apply" (Indeed), otherwise `null` |

Leave out ads for courses or services, and "jobs you may be interested in" blocks that aren't results of this search.

Take a second page (`--page 1`) only when the first page was full (25 on LinkedIn, 10 or more on Indeed) and the run is still under its page-load budget.

**Pace:** wait 10 to 20 seconds between LinkedIn page loads, and a few seconds between Indeed loads. Don't open individual job postings: the results pages have everything above.

**Stop a source** when it shows a CAPTCHA, a "verify you're human" check, an unusual-activity warning or a sign-in wall. Don't try to get around it: skip that source's remaining searches, carry on with the other source, and tell the user what you saw so they can deal with it in their browser.

## 3. Save

After each search, write what it found as a batch file in `postings-raw/` in the job-search folder (gitignored), named `<YYYY-MM-DD>-<source>-<keywords>-<place>.json`:

```json
{
  "source": "linkedin",
  "query": "senior backend engineer",
  "location": "Denver, CO",
  "remote": false,
  "days": 1,
  "url": "<the search URL>",
  "ran_at": "2026-11-27T15:04:05Z",
  "note": "",
  "postings": [
    {"id": "4012345678", "url": "https://www.linkedin.com/jobs/view/4012345678/", "title": "Senior Backend Engineer",
     "company": "Northwind", "location": "Denver, CO (Hybrid)", "posted_text": "2 days ago",
     "salary_text": "$150K/yr - $190K/yr", "easy_apply": true}
  ]
}
```

`ran_at` is the time you read the page, in UTC; the script works out posting dates from it. Put anything odd in `note` ("stopped: verification check", "only 3 results"). A search that found nothing still gets a batch with an empty `postings` list, so the site shows it ran.

Then merge the batches:

```
python <skill dir>/scripts/postings.py add postings-raw/2026-11-27-*.json
```

`add` cleans each posting (posting date, yearly pay in dollars, remote/hybrid/onsite, a plain link), keeps one record per job across runs, and notes when the same job is on both sites (`also_on`). It prints a line per search: found, new, already seen, on the other site, skipped. Re-running it on the same batches changes nothing.

## 4. Report

Run `python <skill dir>/scripts/postings.py list --days <days>` and tell the user, briefly:

- the searches run (and any skipped or stopped, with why);
- how many postings are new this run, and the total in `postings.json`;
- the companies with the most new postings, and any posting that lists pay;
- the five newest that best match the target roles, each with its link.

Finish with where to see it all: on the site's **Jobs > Job finder** page (`https://jarlowrey.github.io/swe-prac/jobs/#/finder`, or the same page on a local build), choose **Import** and pick `postings.json` from the job-search folder. The page charts postings by day, source, company, workplace and pay, and keeps the data in that browser only.

## Ground rules

- Read only. Never click Apply, Easy Apply, Save, "Set alert", Follow or Message, and never fill in anything on LinkedIn or Indeed.
- Keep browsing light: results pages only, at most 6 page loads per source per run, 10 to 20 seconds apart on LinkedIn. The user needs these accounts for their job search.
- Stop a source at the first CAPTCHA, verification check or sign-in wall, and tell the user. Don't retry it in a loop or work around it.
- Search with keywords and places only. Nothing else from the profile goes into a search or a URL.
- Record what the cards show. Don't guess a company, date or pay that isn't there.
