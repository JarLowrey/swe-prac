# Design: moving the payments ledger to an event-sourced service

> Fictional example of a project write-up. Real design docs are often
> employer-confidential, which is why `reference/` is gitignored. The
> job-answers skill uses docs like this for detail but describes the work in
> general terms, leaving out internal system names and internal-only numbers.

Author: Jordan Example · Status: Done (2025) · Team: Payments Platform, Contoso

## Context

The payments ledger lived in tables shared by four services in one PostgreSQL database. Any service could write to them, so reconciling the ledger against card-network settlement files took a person about 3 days each month, and every schema change needed four teams to agree.

## Goals

- One service owns writes to the ledger; everything else reads through it.
- Ledger entries are append-only events, so any balance can be rebuilt and audited.
- Month-end reconciliation runs in hours, not days.
- No downtime and no customer-visible change during the move.

## Non-goals

- Changing how fees are calculated.
- Moving off PostgreSQL.

## Options considered

1. **Single cutover weekend.** Freeze writes, migrate, switch. Fast, but rollback means replaying a weekend of payments by hand.
2. **Dual write with shadow reads, then cohort cutover (chosen).** Write to both stores, compare reads in the background, and move merchants over in cohorts by size. Slower, but every step can be reversed in minutes.
3. **Rebuild the ledger from settlement files.** Clean, but settlement files lag by up to two days, so it can't be the live source.

## Rollout

- Weeks 1–4: ledger service and dual writes behind a flag.
- Weeks 5–10: shadow reads compared on every request; mismatches paged the team. Found two rounding bugs.
- Weeks 11–16: cohort cutover, smallest merchants first. About 80% of volume moved before the holiday freeze; the rest in January.

## Results

- Reconciliation: about 3 days down to about 4 hours.
- No customer-facing incidents during the migration.
- Schema changes to the ledger now need one team's review instead of four.
