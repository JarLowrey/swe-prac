---
name: job-contacts
description: Find people at a target company on LinkedIn (recruiters, talent partners, engineers and engineering managers) whom the user can personally reach out to for a referral, advice or a read on the team, and draft a short personalized note for each. Use this whenever the user wants referrals, networking contacts, recruiters, the hiring manager, or "people to talk to" at a company, and when the job-apply skill starts a new application.
---

# Job contacts

Finds `contacts.count` people (default 3) at a company whom the user could message about a specific role, and drafts a note for each. Settings come from `reference/profile.yaml` in the **job-search folder**: `$JOB_SEARCH_DIR` if set, otherwise the current directory if it contains `reference/profile.yaml`, otherwise `~/job-search`.

The user does the outreach. This skill doesn't send connection requests, messages or InMail, and doesn't follow, like or endorse anything. Each of those goes out under the user's name, so it's their call.

## Who to pick

Cover both routes into the company:

- **At least one recruiter:** a technical recruiter, talent partner or sourcer who hires engineers, ideally for the org this role sits in. Recruiters know whether the role is really open and can pull an application to the top.
- **At least one engineer:** a senior, staff or principal engineer, or an engineering manager, on the team or org named in the posting (or the closest match). Peers give an honest picture of the team and are where most referrals come from.
- **Remaining slot:** whoever is strongest. That's the hiring manager if you can identify them, otherwise another engineer on the team or a second recruiter.

Rank candidates roughly by:

1. **Relevance:** same team or org, same tech area, or the recruiter who posted the job (LinkedIn job pages sometimes show "Meet the hiring team").
2. **Connection:** 1st or 2nd degree, mutual connections, or a school or past employer in common (`contacts.shared_background` in the profile, plus the employers and schools on the resume). Shared background is the main reason a stranger replies.
3. **Near the user:** in or around `location.city`, or one of the areas in `location.acceptable_locations`.
4. **Currently at the company:** check the current position, not past ones.
5. **Active on LinkedIn:** recent posts, or "#hiring" in the headline.

Leave out people who have left, VP-and-above executives unless the company is small, and people at a different company with a similar name. If fewer than the target number are good matches, say so instead of padding the list with weak ones.

If an earlier application to the same company has a `contacts.md` from the last 30 days, start from it and re-tailor the notes for this role.

## Search

Use the user's own signed-in Chrome through Claude in Chrome. Load the tools in one ToolSearch call (`tabs_context_mcp`, `tabs_create_mcp`, `navigate`, `get_page_text`, `find`, `computer`), call `tabs_context_mcp`, and work in a new tab. If LinkedIn shows a sign-in page, ask the user to sign in.

Keep it light. LinkedIn restricts accounts that view lots of profiles quickly or look automated, and the user needs this account for the job search. Budget about 6–8 page loads per company. Search result pages already show name, headline, location and connection degree, which is usually enough. Open a profile only to confirm a shortlisted person's current role when the headline is unclear.

Searches, in order (`<City>` is `location.city` from the profile):

1. If the job is on LinkedIn, check the job page for the poster or "Meet the hiring team".
2. People search with the company and role in the keywords:
   `https://www.linkedin.com/search/results/people/?keywords=<Company>%20technical%20recruiter%20<City>`
   then the team or tech area from the posting, e.g. `<Company> engineering manager <team>` and `<Company> senior engineer <tech area>`. Confirm each result's current company in the headline.
3. If LinkedIn search isn't usable (not signed in, the monthly search limit is hit, or results are thin), fall back to WebSearch: `site:linkedin.com/in "<Company>" "technical recruiter" <City>`. Those results can be out of date, so check the current position on the profile before including anyone.

## Notes to send

For each person, draft:

- **A connection note** under 200 characters, short enough for a free LinkedIn account's connection request.
- **A follow-up message** of 80–120 words for after they accept, or for email.

Tailor each note to the person:

- **Recruiter:** name the exact role, give the single most relevant credential, and ask whether they're the right person to talk to about it.
- **Engineer:** lead with what you have in common if there's anything, and ask for 15 minutes of their perspective on the team. Save the referral ask for the follow-up, after there's been some conversation; people are far more willing to refer someone they've talked to.
- **Hiring manager:** the role, the most relevant credential in one line, and a brief ask to talk.

Keep the voice plain, specific and brief, with no flattery. Mention a shared connection or background first when there is one.

## Output

Write `contacts.md` in the application folder, or reply in chat if there's no folder (see `examples/applications/*/contacts.md`):

```markdown
# Contacts: <Company> (<Role>)
Found <date>. Nothing has been sent; reach out yourself.

| # | Name | Title | Location | Connection | Why them |
|---|---|---|---|---|---|
| 1 | [Full Name](profile URL) | Technical Recruiter, Infrastructure | Denver, CO | 2nd, 4 mutual | Recruits for the org this role is in |

## 1. Full Name, Title
Connection note (<n> chars):
> ...

Follow-up:
> ...
```
