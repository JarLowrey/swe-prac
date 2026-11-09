Build the booking core of a short-term rental marketplace. Two clocks run here: `timestamp` is
when an operation happens, while `check_in`/`check_out` are integer night numbers on the calendar.
Keep them separate; Level 3 depends on it. Level 4 deliberately changes how an earlier method
behaves.

## Approach

Bookings and holds are one `Reservation` type with a `blocks(ts)` method. Every availability check
(`book`, `hold`, `search_available`) asks that one question, so Level 3's holds slot in without
touching the conflict logic.

**Data model.** `listings: dict[id, Listing(price, overrides)]` and `res: dict[rid, Reservation]`
holding both kinds, each with `kind`, `check_in`, `check_out`, `expires_at`, `total`, `cancelled`,
`confirmed`.

## How the crux is handled

- `blocks(ts)`: a booking blocks unless cancelled; a hold blocks while unconfirmed and
  `ts < expires_at`. Expiry is a comparison, never a cleanup job.
- Overlap is the half-open test `r.check_in < check_out and check_in < r.check_out`, so a stay
  ending on night 8 never conflicts with one starting on 8.
- `confirm_hold` marks the hold confirmed (so it stops blocking) and creates a booking with the
  same nights. No conflict check is needed: an active hold already blocked everyone else.
- Pricing lives in one `_night_price(listing, night)` from the start. Level 4's overrides change
  one line, and each booking stores `total` when created, so later price changes can't touch
  revenue.
- `search_available` is written to the Level 4 rule (max nightly price <= limit, sort by total
  quote). With no overrides that is identical to Level 2's rule, so one implementation passes both.

## Complexity

Conflict checks scan all reservations, O(R) per call; `search_available` is O(L × (R + nights)).
At scale you'd index reservations by listing.

## Common mistakes

- Storing holds in a separate structure and forgetting to check it in one of the three call sites.
- `<=` in the overlap test, which makes back-to-back stays conflict.
- Expiry as `ts <= expires_at` (off by one at the boundary).
- Recomputing a booking's price from current prices in `host_revenue`.
- Sorting booking ids as strings, so `booking10` comes before `booking9`.

## Key snippet

```python
def blocks(self, ts) -> bool:
    if self.kind == "booking":
        return not self.cancelled
    return not self.confirmed and ts < self.expires_at

def _free(self, ts, lid, check_in, check_out):
    return not any(
        r.listing == lid and r.blocks(ts) and r.check_in < check_out and check_in < r.check_out
        for r in self.res.values()
    )
```

Remember: one "does this block at ts" predicate, half-open ranges, and lock money in at the moment
of sale.
