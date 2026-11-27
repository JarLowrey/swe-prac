# Research briefs

Four briefs, one `Agent` call each (subagent_type `general-purpose`), all four in ONE message so they run in parallel. Each prompt = the shared preamble + one brief, with every `{placeholder}` filled:

- `{company}`: the company as people search for it ("Northwind Traders", not "northwind").
- `{role}`: the role title from the prompt ("Senior Software Development Engineer").
- `{level}`: the level in plain words ("senior", "staff", "new grad"), read off the title.
- `{team_hint}`: the team, brand or org if the emails or an earlier guide name one; otherwise "none known".
- `{loop_hint}`: one neutral paragraph on what the candidate's emails say about the process: stages done, number, length and type of loop rounds, the coding or interview tool named, interviewer *titles*, rules (NDA, no AI tools). "Nothing yet" if the emails say nothing or the prompt has no email context.
- `{cutoff_year}`: the current year minus 2.

Privacy: a brief carries ONLY those values. Never the candidate's name or email address, recruiter or interviewer names, meeting links, passwords, requisition or candidate ids, or email text. Agents search the open web with what they are given.

---

## Shared preamble

```
You are researching how {company} interviews software engineers, for a candidate preparing for a {level} {role} interview loop. Research only: write no files and publish nothing.

Ground rules
- Search queries name only the company, the role, the level and the team. Never add a person's name or other personal details.
- Open every page you cite (WebFetch). A search-result snippet is not a source. If a site blocks fetching (Glassdoor, Blind and LinkedIn often do), say so and use what other pages quote from it, labelled as such.
- Prefer, in order: the company's own pages (careers site, interview guide, engineering blog, values page); then dated candidate reports (the discussion forums of public coding-practice sites, Blind, Glassdoor, Reddit, levels.fyi, personal blogs, YouTube descriptions).
- Date every claim: when the page was published or when the candidate interviewed. Mark anything from before {cutoff_year} as possibly out of date.
- Count independent reports. One post is one report; say "1 report". Never present a single anecdote as a pattern.
- If the company has several divisions or brands, say which one each report is about, and favour reports that match this team: {team_hint}.
- Stop after about 15 pages opened.

Report format: your whole final message, nothing else, under 900 words.
## Findings
One bullet per claim: the claim · official | candidate report (N) | inference · date · [source title](url)
## Conflicts and gaps
Where sources disagree, and what you looked for and could not find.
## Sources opened
- [title](url) · published or interview date · official | candidate
```

---

## Brief 1: the process

```
Your topic: the shape of {company}'s interview process for a {level} {role}, as it runs now.
- Stages before the final loop (recruiter call, online assessment, technical phone screen, hiring-manager screen) and what each covers.
- The final loop: number of rounds, their length, format (virtual or onsite; the shared coding editor or whiteboard tool used), and which round types it holds (coding, system design, behavioral, domain or past-project deep dive, bar raiser or equivalent). Which interviewer seniority runs which round type, if reported.
- How the decision is made: debrief or hiring committee, team matching, level calibration, typical time from loop to offer.
- Any official candidate guide, prep page or rules the company publishes (for example no AI tools, NDA). Link the official interview guide if one exists.
What the candidate's own scheduling emails already say (check reports against it; don't repeat it as a finding): {loop_hint}
```

## Brief 2: behavioral

```
Your topic: what {company}'s behavioral interviews for a {level} {role} test and ask.
- The company's official values or leadership principles, word for word, with a link, and anything official about how interviews assess them.
- How the behavioral part is run: its own round or folded into others, who runs it, whether it is structured (STAR, competency rubric).
- Questions candidates report being asked, each with date and number of reports. Group them by the value they probe.
- What interviewers reportedly look for at the {level} level: scope, ownership, conflict, influence without authority, mentoring, ambiguity.
What the candidate's own scheduling emails already say: {loop_hint}
```

## Brief 3: coding

```
Your topic: what {company}'s coding interviews for a {level} {role} look like.
- Online assessment, if any: platform, length, number and difficulty of problems.
- Live coding rounds: platform, language choice, classic algorithm puzzles or practical (build a small feature, debug, extend existing code over several levels), whether code must run against tests.
- Specific problems candidates report: a link to the problem on a public practice site where one exists, difficulty, date, number of reports. Aim for 10-20, newest first. Note what a company-tagged problem list on such a site contains if you can see one.
- Topic frequency: which data structures and algorithms come up most.
- Any low-level or object-oriented design round (design classes for a parking lot, an API, an in-memory store).
What the candidate's own scheduling emails already say: {loop_hint}
```

## Brief 4: system design

```
Your topic: what {company}'s system design interviews for a {level} {role} cover.
- Whether the {level} level gets one or more design rounds, their length, the tool used, and how they run (open prompt, deep dive on a past project, API design).
- Design prompts candidates report, each with date and number of reports.
- What {company} actually builds, from its engineering blog and conference talks: the systems behind its main products (for example search, booking, pricing, payments, messaging, data platform, ML). Name 4-6 systems, a link each, with one line on what is hard about each. These become likely prompts.
- What interviewers reportedly grade: requirements, estimates, data model, APIs, scaling, trade-offs, operations.
What the candidate's own scheduling emails already say: {loop_hint}
```
