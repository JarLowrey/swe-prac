This is the classic reservation question ("design a reservation system"), with event ticketing as a common variant. The heart of it is correctness under concurrency; the rest is ordinary scale.

**Requirements.** Functional: search availability for dates; view a property with a calendar; reserve (hold) while paying; confirm; cancel; hosts manage calendars and prices. Non-functional: **[never double-book](#/design/learn/reliability/concurrency-control-and-double-booking)**; search is fast and may be slightly stale; [booking is strongly consistent](#/design/learn/data/picking-a-guarantee-per-operation); handles flash demand for popular listings or events. Clarify: unique listings (a vacation home, one seat) or fungible inventory ("any of 40 standard rooms")? Both are covered below.

**Estimates.** 10M listings, 500K bookings/day ≈ 6/s average, 50/s peak: tiny for writes. Searches: 100M/day ≈ 1,200/s average, 5,000+/s peak, so the read/search side is the scale problem, while booking is a correctness problem. Calendar storage: 10M listings × 365 nights × ~20 bytes = 73 GB; fits one sharded relational database.

**API.**

- `GET /search?location&dates&guests&filters` → listings (served by the search system; see the proximity search question)
- `POST /bookings {listing_id, check_in, check_out, guests}` with [`Idempotency-Key`](#/design/learn/networking/idempotency-keys) → `201 {booking_id, status: HELD, expires_at}`
- `POST /bookings/{id}/confirm` (after payment) → `CONFIRMED`; `DELETE /bookings/{id}` cancels.

**Data model (relational; [this needs transactions](#/design/learn/data/transactions)).**

- `listing(id, host_id, ...)`
- `calendar(listing_id, night, status, price, booking_id)` with a **primary key / [unique key](#/design/learn/data/unique-constraints) on `(listing_id, night)`**: one row per listing-night.
- `booking(id, listing_id, guest_id, check_in, check_out, status, expires_at, idempotency_key UNIQUE)`

Status values: `HELD`, `CONFIRMED`, `CANCELLED`, `EXPIRED`.

**High-level design.** Search and booking need different things, so they take different paths. Search reads an index kept up to date from the database's change events and may lag by seconds. Booking writes to the relational database, the single source of truth, in one transaction.

```mermaid
flowchart TD
  G((Guest)) --> LB[Load balancer]
  LB -->|search| SS[Search service]
  LB -->|"book, confirm, cancel"| BS[Booking service]
  SS --> IX[(Search index<br/>may lag by seconds)]
  BS --> DB[(Relational DB<br/>listing, calendar, booking)]
  BS -->|"charge"| PAY[Payment service]
  SW[Hold sweeper] -->|"release expired holds"| DB
  DB -.->|change events| IW[Indexer]
  IW -.-> IX
```

**Booking flow without double-booking.**

1. In a single transaction: insert a `booking` row (`HELD`, `expires_at = now + 10 min`) and claim every night in the range, either by inserting rows into a `booking_nights(listing_id, night)` table with a unique key `(listing_id, night)`, or with `UPDATE calendar SET status='HELD', booking_id=? WHERE listing_id=? AND night BETWEEN ? AND ? AND status='AVAILABLE'` and checking that [the affected row count](#/design/learn/reliability/atomic-conditional-updates) equals the number of nights.
2. If any night is already taken the constraint/row count fails, the transaction rolls back, and the user sees "no longer available". No application-level locks needed: [the database arbitrates](#/design/learn/data/check-then-act-races).
3. Payment proceeds with the booking's idempotency key (see the payments question). On success, mark `CONFIRMED`; on failure or timeout, release the nights.
4. [A sweeper job](#/design/learn/data/holds-that-expire) releases nights for `HELD` bookings past `expires_at` (and the confirm step re-checks that the hold is still valid).

Two guests asking for overlapping nights at the same moment, each through the booking service:

```mermaid
sequenceDiagram
  participant A as Guest A
  participant DB as Database
  participant B as Guest B
  A->>DB: txn: booking HELD,<br/>claim nights 1 to 3
  B->>DB: txn: booking HELD,<br/>claim nights 2 to 4
  DB-->>A: committed
  DB-->>B: night 2 taken,<br/>rolled back
  Note over A,DB: A gets 201 HELD,<br/>expires in 10 min
  Note over DB,B: B gets 409,<br/>no longer available
```

The booking's status through the flow:

```mermaid
stateDiagram-v2
  [*] --> HELD: nights claimed
  HELD --> CONFIRMED: payment succeeded
  HELD --> CANCELLED: payment failed
  HELD --> EXPIRED: sweeper, past expires_at
  CONFIRMED --> CANCELLED: guest or host cancels
  CANCELLED --> [*]: nights released
  EXPIRED --> [*]: nights released
```

**Fungible inventory (hotel room types).** Keep `inventory(hotel_id, room_type, night, total, reserved)` and book with `UPDATE ... SET reserved = reserved + 1 WHERE reserved < total` for every night in one transaction. Contention concentrates on popular nights, so keep transactions short and ordered consistently by night to [avoid deadlocks](#/design/learn/data/pessimistic-locking-and-deadlocks).

**Deep dives.**

1. **Search vs booking consistency.** Search reads from a search index (Elasticsearch) [fed by change events](#/design/learn/reliability/read-models-and-search-indexes) from the calendar, so it can be seconds stale; showing a listing that was just taken is acceptable because the booking transaction is the final authority. Show "available" optimistically, confirm at booking time, and handle the miss gracefully.
2. **[Hot listings and flash sales](#/design/learn/reliability/hot-rows-and-flash-sales) (ticketing).** Thousands of users want the same seats. Use a virtual waiting room that admits users at a controlled rate, hold seats for a limited time, and serialize writes per event/section through a queue or a single-writer partition. Pre-sharding inventory (sections as separate rows) spreads lock contention.
3. **Holds.** The 10-minute hold is a lease; display the countdown, extend only once, and release on payment failure. The expiry must be enforced server-side, not by the client timer.
4. **Payments and sagas.** Booking spans our database and the payment provider: [model as a saga](#/design/learn/reliability/sagas-and-compensation) (hold, charge, confirm; compensate by releasing the hold and refunding), driven from the booking status. See the payments question.
5. **Host calendar sync.** Hosts also have external calendars (iCal feeds). Sync can be late, so treat them as eventual and accept occasional conflicts that need host cancellation policy; reconcile regularly.
6. **Multi-region.** Keep each listing's calendar in one home region ([single leader](#/design/learn/data/single-leader-replication)) so booking is strongly consistent; replicate reads globally. Cross-region writes for one listing would need consensus and add latency.

**The design after the deep dives.** Green marks what they added or changed.

```mermaid
flowchart TD
  G((Guest)) --> WR[Waiting room<br/>for flash sales]:::good
  WR --> LB[Load balancer]
  LB --> SS[Search service]
  LB --> BS[Booking service]
  SS --> IX[(Search index)]
  BS --> DB[(Relational DB<br/>home region per listing)]:::good
  BS -->|"saga: hold, charge, confirm"| PAY[Payment service]
  SW[Hold sweeper] --> DB
  DB -.->|change events| IW[Indexer]
  IW -.-> IX
  CAL[iCal sync<br/>host calendars]:::good -.-> DB
  DB -.->|"read replicas"| RR[(Other regions)]:::good
```

**Wrap-up.** Metrics: booking success rate, hold-expiry rate, search-to-book conversion, calendar/search index lag, conflicts at booking time. [Reconciliation](#/design/learn/reliability/reconciliation): nightly job verifying every `CONFIRMED` booking has exactly the right calendar rows and a matching payment.
