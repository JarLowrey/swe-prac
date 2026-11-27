Build the booking core of a short-term rental marketplace. `timestamp` is when an operation
happens, while `check_in` and `check_out` are integer night numbers on the calendar.

- `add_listing(timestamp, listing_id, nightly_price) -> bool` adds a listing with a nightly price.
  Returns `False` if the listing already exists.
- `book(timestamp, listing_id, guest_id, check_in, check_out) -> str | None` books nights
  `check_in` through `check_out - 1` (check-out is exclusive). Returns `"booking1"`, `"booking2"`,
  … from a global counter, or `None` if the listing is missing, `check_in >= check_out`, or any
  night overlaps an active booking.
- `cancel(timestamp, booking_id) -> bool` cancels the booking and frees its nights. Returns `False`
  if the booking doesn't exist or is already cancelled.
