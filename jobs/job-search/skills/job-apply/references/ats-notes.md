# Applicant tracking system notes

Tips for the sites job applications usually run on. Read the section for the site you're on. Sites change their layouts; when something here doesn't match what you see, trust the page.

## Contents
- Recognizing the site
- Forms embedded in a careers page
- Greenhouse
- Lever
- Ashby
- Workday
- iCIMS, Taleo / Oracle, SmartRecruiters
- LinkedIn Easy Apply
- Common snags

## Recognizing the site

| URL contains | Site |
|---|---|
| `greenhouse.io`, or `gh_jid=` in a careers-page URL | Greenhouse |
| `jobs.lever.co` | Lever |
| `jobs.ashbyhq.com` | Ashby |
| `myworkdayjobs.com` | Workday |
| `icims.com` | iCIMS |
| `taleo.net`, `oraclecloud.com` | Taleo / Oracle Recruiting |
| `smartrecruiters.com` | SmartRecruiters |
| `linkedin.com/jobs/view` | LinkedIn |

## Forms embedded in a careers page

Company careers pages often embed the Greenhouse, Ashby or iCIMS form in an iframe. If reading the page shows none of the form fields, find the iframe's `src` and open that URL directly in the tab. The form behaves the same and is much easier to read.

## Greenhouse

- One page. Personal info at the top, then resume and cover letter, then custom questions, then the voluntary self-identification section at the bottom.
- Resume: the file input is hidden behind an "Attach" button. Find that input and upload the file to it directly.
- Newer forms (`job-boards.greenhouse.io`) use searchable dropdowns for country, location, yes/no questions and EEO fields. Setting them directly often doesn't take; click the field, type part of the option, then click the matching option or press Enter.
- The location field is an autocomplete: type `location.city` from the profile and choose the full match (e.g. "Denver, Colorado, United States").
- Self-identification asks for gender, Hispanic/Latino, race (sometimes only after the Hispanic/Latino answer), veteran status and disability status.
- The final button is "Submit application". Don't click it.

## Lever

- The form is at `.../<company>/<job id>/apply`. Uploading the resume at the top pre-fills name, email, phone and current company; check them against the profile.
- "Additional information" is an optional free-text box used like a cover letter. Leave it empty unless the user wants something there.
- Custom questions appear as separate cards. The optional U.S. equal-opportunity section at the bottom has gender, race and veteran-status dropdowns.
- The final button is "Submit application". Don't click it.

## Ashby

- The form is on the job's "Application" tab. "Autofill from resume" at the top parses the upload; wait for it to finish, then check every pre-filled field.
- Yes/no questions are often a pair of buttons; click the right one.
- The self-identification section is at the end.
- The final button is "Submit Application". Don't click it.

## Workday

- Every company has its own Workday account. The user signs in or creates the account; then choose "Apply" and either "Autofill with Resume" (upload the resume, then check everything) or "Apply Manually". Autofill is faster, but its work-history parse is often messy: compare each job's title, employer and dates against the resume.
- A multi-step wizard: My Information, My Experience, Application Questions, Voluntary Disclosures, Self Identify, Review. "Save and Continue" saves the step and is safe to click. The "Submit" button on the Review step is the one to leave alone.
- Dropdowns are custom widgets: click to open, then click the option (or type and press Enter). "How did you hear about us" is often a nested list: pick a category, then the item.
- Date fields are split into month and year boxes: click each and type.
- Voluntary Disclosures covers gender, ethnicity and veteran status, and usually has a terms acknowledgment checkbox that the user ticks.
- Self Identify is the federal disability form: name, today's date, and the option matching `eeo.disability_status`.

## iCIMS, Taleo / Oracle, SmartRecruiters

- Usually require an account (the user creates it) and run as multi-step forms. Follow the Workday approach: fill one step, re-read it, continue, and stop on the final review page.
- iCIMS normally puts the form inside an iframe; open the iframe URL directly (see "Forms embedded in a careers page").

## LinkedIn Easy Apply

- A multi-step pop-up: contact info (pre-filled from the LinkedIn profile), resume (pick the uploaded one or upload `resume.path`), additional questions, voluntary self-identification, then review. "Next" and "Review" are safe; "Submit application" is not.
- Screening questions often want a whole number of years. Answer from the resume; flag it if the resume doesn't make the number clear.
- If the company also has the job on its own careers site, tell the user. Some prefer to apply there.

## Common snags

- **A value doesn't stick.** Custom widgets ignore programmatic values. Click the field and type instead, then re-read the section.
- **"Human check" questions.** Some forms (Lever especially) tell applicants to start an answer with a code word or write in all lowercase to prove a human wrote it. Draft these in `answers.md` but leave the field empty for the user to fill in; see step 4 of the main skill.
- **Required fields.** Look for asterisks and "required" labels before finishing. Don't press Submit to find out what's missing.
- **Phone with a separate country dropdown.** Choose United States (+1) and enter the number without the country code.
- **The page reloads empty** after a long fill (session timeout). Tell the user and refill from the profile; the drafts in `answers.md` are still there.
