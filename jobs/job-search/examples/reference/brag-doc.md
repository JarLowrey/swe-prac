# Brag doc: Jordan Example

> Fictional example. Your real `reference/` folder is gitignored. Keep a running
> list like this one, with numbers you can defend, and the job-answers skill
> will pull from it.

## Contoso, Payments Platform (Senior Software Engineer)

### 2026 H1
- **Idempotent callback handling.** Card-network callbacks were retried on timeout and occasionally applied twice, causing about two duplicate-charge incidents a quarter. Traced it from vague support tickets to the retry path, designed idempotency keys stored with the ledger entry, and rolled it out behind a flag. Zero duplicate-charge incidents in the two quarters since.
- Wrote the team's guide to safe schema changes (online migrations, backfills in batches, rehearsal on a production-sized copy).

### 2025 H2
- **Ledger migration finished.** Moved the payments ledger off shared database tables onto an event-sourced ledger service. Dual writes plus shadow reads for six weeks, then cut over by merchant cohort. No customer-facing incidents. Month-end reconciliation went from about 3 days to about 4 hours. Design: `ledger-migration-design.md`.
- Promoted to Senior Software Engineer in the 2025 cycle (feedback cited the migration plan and the mentoring below).

### 2025 H1
- **On-call redesign** for the team's 6 services. Audited every alert, deleted or merged two-thirds of them, and replaced the rest with SLO-based burn-rate alerts. Pages per week dropped from about 40 to about 8. On-call satisfaction (team survey) went from 2.1 to 4.0 out of 5.
- Mentored 4 engineers through their first on-call rotations and design reviews; two have since been promoted to senior.

## Fabrikam, Order Management (Software Engineer), 2017–2021

- Built the order-routing service (Go, PostgreSQL, Kafka) that picks a fulfillment center for each order; it handled about 2M orders a day at holiday peak.
- Moved CI from a shared build box to containerized pipelines. Median build time dropped from 22 to 7 minutes.
- Ran a redesign of the backend interview loop: replaced puzzle questions with a practical design exercise and wrote the rubric. Used for about 60 hires.
- Caused, and then led the post-mortem for, an 11-minute order-table lock during peak (see `behavioral-stories.md`, "A failure").

## Outside work

- Co-organizer of the Denver Gophers meetup since 2022 (monthly, about 80 regulars).
