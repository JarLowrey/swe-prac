- `set_night_price(timestamp, listing_id, night, price) -> bool` overrides the price for one night
  of the listing. Returns `False` if the listing doesn't exist.
- `quote(timestamp, listing_id, check_in, check_out) -> int | None` returns the total price for
  nights `check_in` through `check_out - 1`, using overrides where set and `nightly_price`
  otherwise. Returns `None` for a missing listing or `check_in >= check_out`. Availability does
  not matter.
- `host_revenue(timestamp, listing_id) -> int | None` returns the sum of locked-in totals for the
  listing's non-cancelled bookings (`0` if there are none). Returns `None` if the listing doesn't
  exist.

Every booking locks in its quoted total at the moment it is made (for a confirmed hold, at
confirm time). Later price changes don't affect it.

**Changed behaviour:** `search_available` now keeps a listing only if every night in the range
costs `<= max_price`, and sorts by total quote ascending, then listing id ascending. With no
overrides this gives the same results as the Level 2 rule, so earlier tests still pass.
