- Treat bookings and holds as one `Reservation` record (a `@dataclass`) with a `kind` and an
  optional `expires_at`, plus an `is_active(r, ts)` check. Every availability check filters on it.
- Overlap test for half-open ranges: `a_in < b_out and b_in < a_out`.
- Put pricing in one `night_price(listing, night)` function from Level 1, so Level 4's overrides
  touch a single place.
- Sort ids numerically by parsing the suffix, e.g. `int(booking_id.removeprefix("booking"))`, or
  store the counter value on the record and sort by that.
