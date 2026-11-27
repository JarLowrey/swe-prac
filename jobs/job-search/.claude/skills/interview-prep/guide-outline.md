# The study guide

One guide per company, titled `<Company> Interview Guide` (the company as the prompt names it). Written for the user to study from in the days before a loop: plain, specific, every candidate-reported claim dated and sourced.

## Starting it

**As a Claude Docs doc** (one `batch`, then `open` the link it returns). Byline: as-of date chip (today) · mention of the user. Then one pending block per section, in the order below. Put "(research running)" at the end of an intent while its agent is still out.

**As a markdown file** (`guides/<company-slug>-interview-guide.md`): `# <Company> Interview Guide`, a line `As of <date>`, then each section's heading with `_Research running._` under it, replaced as each section is filled.

| Key | Pending intent |
| --- | --- |
| `lead` | At a glance: the loop in two sentences and the three things to prepare first |
| `s1` | The loop: each round, its format and what it tests, from your emails and candidate reports |
| `s2` | Behavioral: {Company}'s values, the questions candidates report, and which of your stories answers each |
| `s3` | Coding: the assessment format, reported problems with links, and a practice order |
| `s4` | System design: prompts drawn from what {Company} builds, and what interviewers grade |
| `s5` | Questions to ask them, and a prep checklist |
| `s6` | Sources: every page the research opened, with its date and whether it is official or a candidate report |

## Filling it

A doc: one `update` per section, each a `replace` of its pending block with `## <heading>` + body, `"as":"markdown"`. A file: edit that section in place. Fill a section as soon as its agent reports; fill `lead` last.

**Lead** (no heading): 2-3 sentences. The loop's shape with dates, then the three highest-value things to prepare. Example: "Your loop is four 1-hour video rounds on Nov 19, 20 and 24. Prepare ..."

**`## The loop`** (from brief 1 + the emails)
- First sentence: the stages done and what is left, with dates.
- A table: `Date | Round | Interviewer title | Format | What it likely tests`. Dates and titles come from the emails; "likely tests" comes from candidate reports and says so. If the emails don't give a schedule, use the stages candidates report instead.
- 2-4 bullets: decision process, rules (NDA, no AI tools, the coding tool), anything official about the process, each linked.
- Never: meeting links, passwords, phone numbers, interviewer or recruiter names, requisition or candidate ids.

**`## Behavioral`** (from brief 2 + the user's stories in `reference/`)
- First sentence: how behavioral is assessed (its own round or folded into each round).
- The company's values, each one line, linked to the official page.
- A table: `Likely question | Value it probes | Your story | Reports`. "Your story" names the user's story that best fits the question, by the title it has in their stories file. 8-12 rows, most-reported first. "Reports" = count and newest date ("3, Oct 2026"). No stories in `reference/`: drop the column and say in one line that adding them (see `examples/reference/behavioral-stories.md`) lets the guide match questions to them.
- One line on what reportedly separates senior answers.

**`## Coding`** (from brief 3)
- First sentence: format and tool (live shared editor, online assessment, language rules).
- A table of reported problems: `Problem | Topic | Difficulty | Reports`, the problem cell linked (to the problem on a public practice site where one exists, else the report). Newest and most-reported first, 8-20 rows.
- Topic frequency in one sentence, not a chart, unless there are 5+ topics with real counts.
- A practice order as `- [ ]` tasks (6-10), easiest-value first. Link the SWE Practice pages below where a topic matches.

**`## System design`** (from brief 4)
- First sentence: whether and where design shows up at this level, and the format.
- Reported prompts (bullets, each dated and linked).
- A table: `Likely prompt | The {Company} system behind it | What makes it hard`, 4-6 rows, built from the engineering blog findings, each system linked.
- What interviewers grade, one line. Link the matching SWE Practice design pages below once, at the end.

**`## Questions to ask and checklist`**
- 4-6 questions for the interviewers, tied to what the research found (team, systems, how success is measured).
- `- [ ]` prep tasks with the date they're needed by, ending with day-of items (test the coding tool's link, a quiet room, no AI tools unless allowed).

**`## Sources`**
- Every page an agent opened, one bullet each: `[title](url) · date · official | candidate`. Official first, then newest first. Note sites that blocked fetching.
- If an earlier guide for this company exists, link it here and in the lead.

## SWE Practice pages to link

The study pages and timed practice on the SWE Practice site. Link the specific page that matches a topic, not the list.

| Topic | Page |
| --- | --- |
| How to approach a coding problem | https://jarlowrey.github.io/swe-prac/practice/#/algo/learn/approach |
| Big O and complexity | https://jarlowrey.github.io/swe-prac/practice/#/algo/learn/complexity |
| Data structures (hash maps, heaps, trees, graphs) | https://jarlowrey.github.io/swe-prac/practice/#/algo/learn/data-structures |
| Problem patterns (two pointers, sliding window, BFS/DFS, intervals, ...) | https://jarlowrey.github.io/swe-prac/practice/#/algo/learn/patterns |
| Dynamic programming | https://jarlowrey.github.io/swe-prac/practice/#/algo/learn/dynamic-programming |
| Timed algorithm problems | https://jarlowrey.github.io/swe-prac/practice/#/algo |
| Multi-level coding assessment practice (build and extend a small system) | https://jarlowrey.github.io/swe-prac/practice/#/coding |
| System design: the interview framework | https://jarlowrey.github.io/swe-prac/practice/#/design/framework |
| System design: networking and APIs | https://jarlowrey.github.io/swe-prac/practice/#/design/learn/networking |
| System design: data (storage, indexing, sharding, replication) | https://jarlowrey.github.io/swe-prac/practice/#/design/learn/data |
| System design: building blocks (caches, queues, load balancers) | https://jarlowrey.github.io/swe-prac/practice/#/design/learn/building-blocks |
| System design: reliability and correctness | https://jarlowrey.github.io/swe-prac/practice/#/design/learn/reliability |
| Timed system design questions | https://jarlowrey.github.io/swe-prac/practice/#/design |

## Check before calling it done
- Nothing a single candidate reported is written as fact; counts and dates are visible.
- No personal data from the emails beyond dates, round types, interviewer titles and the tool named.
- Every table cell is filled or the column is dropped; no "n/a".
