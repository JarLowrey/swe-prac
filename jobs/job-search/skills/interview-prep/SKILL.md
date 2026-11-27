---
name: interview-prep
description: Research how a company interviews software engineers (the loop, behavioral, coding and system design rounds) and write a sourced study guide for it, mapping likely behavioral questions onto the user's own stories. Use when the user runs /interview-prep, or asks for a study guide or interview research for a company they're interviewing with.
argument-hint: "<company>, then optionally Role:, Status: and the email context the tracker's Skills page adds"
---

# Interview study guides

Turns one company into a researched study guide: a doc when you have a docs connector, otherwise a markdown file in the job-search folder.

Files beside this one:
- `research-briefs.md`: the four research briefs, the shared rules, and the report format.
- `guide-outline.md`: the guide's outline and what goes in each section.

Paths are relative to the **job-search folder**: `$JOB_SEARCH_DIR` if set, otherwise the current directory if it contains `reference/profile.yaml`, otherwise `~/job-search`.

## What the prompt gives you

The Skills page of the SWE Practice site builds the prompt:

```
/interview-prep <company>

Role: <role, or "not stated">
Status: <the tracker's status> (latest email <date>)

What my email says about this application is below, for context. ...

## Applications at <company> (n)
...
## Emails (n found, the newest k shown)
...
```

Only the first line is certain. Role, Status and the email context are there when the user picked an application from their tracker. The context is the user's own mail with sender addresses removed: treat it as private data. Read it for the loop's dates and rounds, interviewer *titles*, the coding tool named, and rules (NDA, no AI tools). Never copy names, meeting links, passwords, phone numbers, requisition or candidate ids, or email text into a brief, a search or the guide.

No role given: ask for it in one line, or go on with "software engineer" if the user says so.

## Steps

1. **Context.** Note the role, its level (read off the title: "senior", "staff", "new grad"), the status, and what the emails say about the process. Write the `{loop_hint}` paragraph research-briefs.md describes.
2. **Start the research.** One research agent per brief in research-briefs.md, all four started at once, with every placeholder filled. Only the values listed there go into a brief.
3. **While they run:**
   - Start the guide as guide-outline.md says (title `<Company> Interview Guide`). With a docs connector, create the doc and give the user its link. Without one, write the outline to `guides/<company-slug>-interview-guide.md` (lowercase, hyphens) in the job-search folder, creating `guides/` if needed; the kit's .gitignore keeps it out of git.
   - Read the user's stories in `reference/` (behavioral stories, brag doc, project write-ups; markdown, PDF, .txt, .docx via `skills/job-answers/scripts/docx_to_text.py`), and any `reference_docs` the profile links if you have Google Drive access. The Behavioral section maps questions onto those stories. Never draw facts from `examples/`: those are fake.
   - Look for an earlier guide for this company (a doc of yours titled with the company's name, or the file in `guides/`). If there is one, update it instead of starting another: read it, then replace its sections.
4. **Fill the guide** one section at a time as each agent reports, following guide-outline.md. Lead last. Weigh the reports: official over candidate, recent over old, several reports over one. Say where sources disagree.
5. **Check** the guide against the list at the end of guide-outline.md.

## Report

One line: the guide's title as a link (the doc's link, or the file's path), and one sentence on what the research found that matters most. If it is a doc, add that the user can paste its link into the application's **Study guide** box in the tracker, so it shows on that application. No recap of the guide.
