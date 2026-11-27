- `hold(timestamp, listing_id, guest_id, check_in, check_out, ttl) -> str | None` reserves nights
  for a guest while they pay. Returns `"hold1"`, `"hold2"`, … from a separate counter (holds and
  bookings are numbered independently), with the same failure rules as `book`.
- `confirm_hold(timestamp, hold_id) -> str | None` turns an active hold into a booking with the
  next booking id, keeping the hold's guest and nights, and returns that booking id. Returns
  `None` if the hold doesn't exist, is expired, or was already confirmed.

A hold created at `created_at` is active while `timestamp < created_at + ttl`. Active holds block
`book`, other `hold`s and `search_available` exactly like bookings. Expired holds block nothing.

`guest_bookings` never lists holds.
