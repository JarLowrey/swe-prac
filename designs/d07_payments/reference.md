**Requirements.** Functional: a merchant or app charges a customer's payment method; refunds; payment status; [webhooks to merchants](#/design/learn/networking/webhooks); a ledger and reporting. We integrate with external processors/card networks rather than building them. Non-functional: money is never lost, created or double-charged; every operation is auditable; idempotent under retries; secure (PCI scope kept minimal); high availability for charging, strong consistency for balances.

**Estimates.** 10M payments/day ≈ 120/s average, 1,000/s peak. This is low volume with extreme correctness requirements, so the design optimizes for correctness and auditability, not raw throughput. Each payment produces several ledger entries and state transitions (maybe 10 rows), so 100M rows/day, about 10,000 row writes/s at peak: still modest for a relational database [sharded a few ways, at a few thousand writes/s per primary](#/design/learn/building-blocks/estimation-and-benchmarks).

**API.**

- `POST /payments {amount, currency, payment_method_token, merchant_id}` with a required [`Idempotency-Key`](#/design/learn/networking/idempotency-keys) → `202/201 {payment_id, status}`
- `GET /payments/{id}`; `POST /payments/{id}/refunds` (also idempotent)
- Webhook to merchant: `payment.succeeded | failed | refunded`, signed, [retried with backoff](#/design/learn/reliability/retries-with-backoff-and-jitter).

Card data is tokenized by a secure vault (or the processor's hosted fields) so our servers never touch raw card numbers, which keeps PCI scope small.

**Data model (relational, strongly consistent).**

- `payment(id, merchant_id, amount, currency, status, idempotency_key UNIQUE per merchant, provider_ref, created_at)`
- `payment_event(payment_id, seq, type, payload, at)`: append-only history of every transition.
- **[Double-entry ledger](#/design/learn/reliability/double-entry-ledgers):** `ledger_entry(id, account_id, payment_id, direction DEBIT/CREDIT, amount, currency)`; every transaction posts equal debits and credits across accounts (customer, merchant, fees), so the books always balance and any imbalance reveals a bug. Money amounts are integers in minor units (cents) with an explicit currency, never floats.

**Payment state machine.** `CREATED → PENDING (sent to provider) → SUCCEEDED | FAILED`, then `REFUND_PENDING → REFUNDED`. Allow only legal transitions, enforce them with [conditional updates](#/design/learn/reliability/atomic-conditional-updates) (`WHERE status = 'PENDING'`), and never delete.

```mermaid
stateDiagram-v2
  [*] --> CREATED: row and key inserted
  CREATED --> PENDING: sent to provider
  PENDING --> SUCCEEDED: approved
  PENDING --> FAILED: declined
  SUCCEEDED --> REFUND_PENDING: refund requested
  REFUND_PENDING --> REFUNDED: provider confirmed
  note right of PENDING
    A timeout leaves it here
    until reconciliation settles it
  end note
```

**High-level design.** The payment service owns one relational database holding payments, their events, the ledger and an outbox. Card numbers go from the customer's browser to a vault and never reach our servers. Events leave through the outbox to the webhook service and other consumers.

```mermaid
flowchart TD
  CU((Customer)) -->|"card number"| V[Card vault]
  V -.->|token| MC((Merchant))
  MC -->|"POST /payments,<br/>Idempotency-Key"| API[Payments API]
  API --> PS[Payment service]
  PS --> DB[(Payments DB<br/>payment, events,<br/>ledger, outbox)]
  PS -->|"key = payment_id,<br/>explicit timeout"| PR[Processor]
  RW[Reconciliation worker] -->|"what happened to p1?"| PR
  RW -->|"settle p1"| PS
  DB -.->|outbox| K[[Event stream]]
  K --> WH[Webhook service]
  WH -->|"signed, retried"| MC
```

**Flow.**

1. API receives the request; inserts the `payment` row with the idempotency key in one transaction (a duplicate returns the stored result).
2. The payment service calls the provider with our `payment_id` as the provider-side idempotency key. This call has [an explicit timeout](#/design/learn/reliability/timeouts-and-deadlines).
3. On a definite response, update status and post ledger entries in **one transaction**, plus [an outbox event](#/design/learn/reliability/the-outbox-pattern).
4. The outbox publishes `payment.succeeded`; the webhook service notifies the merchant; downstream systems (receipts, analytics) consume the event.
5. On a **timeout or unknown outcome**, status stays `PENDING`; do not assume failure. [A reconciliation worker](#/design/learn/reliability/reconciliation) queries the provider for the real outcome (by `payment_id`) and settles it.

Step 5, the unknown outcome, with the merchant retrying meanwhile:

```mermaid
sequenceDiagram
  participant M as Merchant
  participant PS as Payments
  participant P as Processor
  M->>PS: POST /payments, key k1
  PS->>PS: insert p1, PENDING
  PS->>P: charge, key p1
  P--xPS: connection drops,<br/>outcome unknown
  PS-->>M: 202, p1 PENDING
  M->>PS: retry with key k1
  PS-->>M: same p1, PENDING,<br/>no second charge
  Note over PS,P: later, the reconciliation worker
  PS->>P: what happened to p1?
  P-->>PS: succeeded
  PS->>PS: one transaction:<br/>p1 SUCCEEDED, ledger<br/>entries, outbox event
```

**Deep dives.**

1. **[Exactly-once effect](#/design/learn/reliability/charging-a-card-exactly-once).** Retries are inevitable (client retries, queue redelivery, our own timeouts). Idempotency keys at our API, a unique constraint inside the transaction, and the provider-side key together make the effect happen once. State plainly: [delivery is at-least-once](#/design/learn/reliability/delivery-guarantees), effects are exactly-once through idempotency.
2. **The unknown-outcome problem.** The classic failure is "we called the provider and the connection died." Never retry blindly with a new key; retry with the same key, or query status. Poll or receive the provider's webhook, and reconcile.
3. **Reconciliation.** Daily (and continuous where possible) compare our ledger with processor settlement files and bank statements. Differences become tickets, never silent fixes. This is the safety net under everything else and a mark of production maturity.
4. **[Multi-step flows (sagas)](#/design/learn/reliability/sagas-and-compensation).** Authorize, then capture (when the goods ship); marketplace payouts; booking holds. Model each as a state machine with compensations (void, refund).
5. **Consistency and sharding.** Shard the payment and ledger tables [by merchant or account ID](#/design/learn/data/choosing-a-partition-key); keep an account's entries on one shard so balance checks are local transactions. [Cross-account transfers](#/design/learn/data/transactions-across-partitions-and-services) use a saga or a two-phase ledger posting (pending, then posted), not distributed locks.
6. **Security and compliance.** Tokenization, encryption at rest and in transit, least-privilege access, audit logs, fraud checks (rule engine and ML score before authorization, with a synchronous decision budget of tens of milliseconds), and strong authentication (3-D Secure) where required.
7. **Webhooks.** At-least-once delivery with signatures and event IDs [so merchants can dedupe](#/design/learn/reliability/deduplicating-consumers); exponential backoff for up to a few days; a dashboard to replay.

**The design after the deep dives.** Green marks what they added or changed.

```mermaid
flowchart TD
  MC((Merchant)) --> API[Payments API]
  API --> FR[Fraud checks<br/>rules and ML score]:::good
  FR --> PS[Payment service<br/>auth and capture as sagas]:::good
  PS --> PR[Processor]
  PS --> DB[(Payments and ledger<br/>sharded by merchant)]:::good
  DB -.->|outbox| K[[Event stream]]
  K --> WH[Webhook service]
  WH -->|"signed, event IDs,<br/>backoff for days"| MC
  OPS[Replay dashboard]:::good --> WH
  SF[(Settlement files,<br/>bank statements)]:::good --> RC[Reconciliation<br/>diffs become tickets]:::good
  RC --> DB
```

**Wrap-up.** Metrics: success rate by provider/issuer, pending-aged count, reconciliation diffs, p99 latency, webhook lag. Multi-provider routing with fallback (if one processor is down, route to another) improves availability but needs care so one payment isn't charged twice across providers.
