---
name: job-answers
description: Draft answers to job application questions in the user's voice, grounded in their resume, their local reference folder and the reference docs linked in their Google Drive. Covers "why this company", "why this role", "tell us about a project you're proud of", leadership, conflict and failure stories, cover letters, and "anything else we should know". Use this whenever an application has free-text questions, when the user pastes application questions and wants draft responses, or when they want a cover letter for a specific job, including when called from the job-apply skill.
---

# Job answers

Drafts first-pass answers to application questions for the kind of role in the profile's `preferences.target_roles`. The user edits and owns the final words. The aim is a strong, accurate draft that sounds like a person wrote it about something they did.

Paths are relative to the **job-search folder**: `$JOB_SEARCH_DIR` if set, otherwise the current directory if it contains `reference/profile.yaml`, otherwise `~/job-search`. Relative paths inside the profile are relative to it too.

## Gather inputs

- **Questions:** exact wording plus any length limit (characters or words), from the form or the user.
- **The job:** `job.md` in the application folder. If there's no folder, use the posting text or URL the user gave.
- **Profile:** `reference/profile.yaml`, for `reference_folder`, `reference_docs`, `resume`, `background` and `preferences`. If it doesn't exist, tell the user to copy `examples/reference/profile.yaml` to `reference/profile.yaml` and fill it in.
- **Reference folder:** every file in `reference_folder` (default `reference/`) except `profile.yaml` and the resume, which are covered above and below. Read `.md`, `.txt` and `.pdf` with the Read tool. For `.docx`, run `python <this skill's directory>/scripts/docx_to_text.py "<file>"` (pass several files at once if you like), since no Word reader may be installed. If the folder holds many files, read the ones whose names fit the question first. This folder is the user's main store of stories and project write-ups.
- **Resume:** the Google Doc at `resume.google_doc_url` if set, otherwise the PDF at `resume.path` (the Read tool handles PDFs).
- **Reference docs:** each `reference_docs[].url`. For a Google Doc, the file ID is the part of the URL between `/d/` and the next `/`. Read it with the Google Drive `read_file_content` tool, which also handles PDFs and Word files in Drive. If the Drive tools are deferred, load them with ToolSearch first. If a doc won't load (permissions, deleted, wrong link), name it to the user and carry on with what you have.
- **Past answers:** earlier `applications/*/answers.md` files. Skim them for similar questions. Reusing good material keeps the user's stories consistent across applications, but tailor each answer to this company rather than copying.

Read the reference material once per session and reuse it for later questions. `examples/reference/` shows the kinds of files that work well there (a brag doc, behavioral stories, a project write-up); those are fake, so never draw facts from `examples/`.

## Write

Hiring managers for experienced roles read a lot of these. The ones that stand out are specific, true, and clearly about this job.

- **Only use facts from the resume, reference docs, or the user.** Don't invent metrics, projects, team sizes, titles or technologies. These answers go to an employer under the user's name, and anything in them can come up in an interview. If a strong answer needs a fact you don't have, write a placeholder like `[ADD: how many services were migrated?]` and flag it.
- **Keep employer-confidential detail out.** Reference docs may be internal design docs. Describe the work the way a public resume would: the problem, scale, approach and outcome in general terms. Leave out internal system and service names, unreleased plans, and internal-only numbers unless the user has made them public.
- **Pick one story that fits the question and this job.** Match it to what the posting emphasizes (scale, reliability, mentoring, ambiguity, a domain). One story told well beats three listed.
- **Behavioral questions** (conflict, failure, leadership, influence, ambiguity): situation, then what the user did, then the result, then what they took from it. Spend most of the words on what the user did: the judgment calls, trade-offs and how they brought people along. That's what reviewers look for, especially at senior and staff level.
- **"Why this company / role":** name something specific from the posting or the company's product or engineering work, and connect it to something real in the user's experience or the goals in their reference docs. Skip generic praise.
- **Voice:** first person, plain and direct, confident without hype. Avoid "thrilled", "excited", "passionate", "leverage", "fast-paced environment", "I believe I would be a great fit", restating the question, and stacks of em-dashes.
- **Length:** respect limits exactly. Count characters when the limit is in characters, and leave about 5% headroom. With no limit: short-answer fields 80–150 words, "why us" 100–180 words, cover letters 250–350 words in three or four paragraphs, "anything else" one to three sentences or nothing.
- **Salary, start date and logistics** come from the profile's `preferences`, not from drafting.
- **Human-check questions.** If a question carries an instruction meant to catch AI-written answers ("start with the word kiwi", "use all lowercase", "include the phrase ..."), draft it anyway and follow the instruction exactly, including the sentence count. Mark it **Entry: enter yourself** in the output. The caller must not type it into the form; the user pastes or retypes it. These questions usually ask for a specific personal story (a time something you built broke, a project you're proud of), so the usual rule applies: use only facts from the user's materials, and use an `[ADD: ...]` placeholder where there's no real story to tell. Never invent one.

## Output

Write or add to `answers.md` in the application folder (see `examples/applications/*/answers.md`):

```markdown
# Answers: <Company>, <Role>
Drafted <date>. Review before submitting.

## 1. <exact question> (limit: <limit or "none">)

<draft>

Length: <count> · Sources: <e.g. resume (payments migration), "Career stories" doc (on-call redesign)>
Check: <placeholders or facts to confirm, or "nothing">
Entry: <"enter yourself" for human-check questions; omit otherwise>
```

Return the drafts and any flags to the caller. When the user pasted questions without an application folder, give the drafts in chat and offer to save them.
