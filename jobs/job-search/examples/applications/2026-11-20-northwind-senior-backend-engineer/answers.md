# Answers: Northwind Traders, Senior Backend Engineer
Drafted 2026-11-20. Review before submitting.

> Fictional example of the `answers.md` the job-answers skill writes.

## 1. Why do you want to work at Northwind Traders? (limit: 1,000 characters)

Moving from batch payouts to near-real-time payouts is the kind of change I like working on: the money has to stay correct while the system underneath it changes. At Contoso I moved our payments ledger off shared database tables onto an event-sourced service with dual writes, shadow reads and a cohort-by-cohort cutover, with no customer-facing incidents. Month-end reconciliation went from about three days to about four hours. Faster payouts put more weight on exactly those things: idempotency, reconciliation, and being able to roll back any step. I'd also like to work on a marketplace where every payment has three parties, which makes the ledger design more interesting than a two-party checkout. And the hybrid option in Denver works well for me.

Length: 755 characters · Sources: resume (ledger migration), `ledger-migration-design.md`, posting (payouts project, three-party payments)
Check: nothing

## 2. Describe a technically complex project you led and the impact it had. (limit: none)

At Contoso our payments ledger lived in tables that four services could write to directly. Reconciling it against card-network settlement files took someone about three days every month, and any schema change needed four teams to agree.

I led the move to a single ledger service built on append-only events. The hard part was doing it without downtime on the system of record for money. I pushed back on a single cutover weekend and proposed a staged plan instead: dual writes behind a flag, six weeks of shadow reads that compared both stores on every request, then cutting merchants over in cohorts, smallest first. The shadow reads caught two rounding bugs before any customer saw them.

We moved about 80% of volume before the holiday freeze and the rest in January, with no customer-facing incidents. Reconciliation dropped to about four hours, and ledger schema changes now need one team's review instead of four. [ADD: team size on the migration?]

Length: 159 words · Sources: `ledger-migration-design.md`, `behavioral-stories.md` (cutover disagreement), resume
Check: fill in the team size placeholder, or delete that sentence
