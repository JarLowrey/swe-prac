# Behavioral stories: Jordan Example

> Fictional example. Write your real stories in the same shape (situation, what
> you did, result, what you learned) and save them in `reference/`. The
> job-answers skill picks the one that best fits each question.

## Disagreement with a stakeholder: the ledger cutover date

**Situation.** The payments product lead wanted the ledger migration cut over in one weekend so it would land before the holiday code freeze. I thought a single cutover of every merchant at once was the riskiest way to change the system of record for money.

**What I did.** Instead of arguing in the meeting, I wrote a one-page comparison of a single cutover against a staged one: what could go wrong, how we'd detect it, and how long rollback would take in each case. I proposed a middle path: dual writes and shadow reads first, then cutting over merchant cohorts in order of size, which would still move about 80% of volume before the freeze. I went through the page with the product lead one-on-one before the planning review, so the review was a decision, not a debate.

**Result.** We went with the staged plan. 80% of volume moved before the freeze and the rest in January, with no customer-facing incidents. The shadow reads caught two rounding bugs that a single cutover would have shipped.

**What I learned.** Put the disagreement in writing, with the other person's goal (the date) treated as a real constraint rather than an obstacle.

## A failure: locking the orders table at peak

**Situation.** At Fabrikam I ran a schema migration that added a column with a default value to the orders table. On our staging data it took seconds. In production, during a weekday peak, it held a lock for 11 minutes. Orders queued and customers saw delays; nothing was lost.

**What I did.** I called the incident myself, rolled back the deploy, and ran the post-mortem. I brought in an online schema-migration tool, added a migration review checklist, and set up a staging copy refreshed weekly at production size so rehearsals were realistic.

**Result.** We had no lock-related incidents in my remaining two years there, and the checklist was adopted by two other teams.

**What I learned.** Rehearse against production-shaped data, and treat "it was fast in staging" as untested.

## Leading without authority: the on-call cleanup

**Situation.** Our team's alerts paged about 40 times a week, most of them noise. Everyone complained; nobody owned fixing it.

**What I did.** I volunteered to own it for a quarter. I audited every alert with the engineer who had written it, deleted or merged two-thirds, and replaced the rest with SLO-based burn-rate alerts. I kept the old alerts running silently for two weeks alongside the new ones, so we could show nothing important would be missed.

**Result.** Pages dropped to about 8 a week, and on-call satisfaction went from 2.1 to 4.0 out of 5. Two neighboring teams copied the approach.

## Ambiguity: the duplicate charges nobody could reproduce

**Situation.** Support reported a handful of duplicate charges each quarter with no pattern anyone could find.

**What I did.** I joined support tickets against ledger entries and callback logs and found every duplicate followed a network timeout and retry. I designed idempotency keys stored with each ledger entry and shipped them behind a flag, one card network at a time.

**Result.** Zero duplicate-charge incidents in the two quarters since.
