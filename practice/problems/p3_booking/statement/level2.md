- `search_available(timestamp, check_in, check_out, max_price) -> str` returns every listing that
  is free for the whole range (nights `check_in` through `check_out - 1`) and has
  `nightly_price <= max_price`, formatted `"listingA, listingB"`. Sort by price ascending, then
  listing id ascending. Returns `""` if none.
- `guest_bookings(timestamp, guest_id) -> str` returns the guest's active bookings formatted
  `"booking1(listingA, 3-5), booking4(listingB, 7-9)"`, where `3-5` is `check_in-check_out`. Sort by
  `check_in` ascending, then booking id ascending. Returns `""` if the guest has none.

Booking ids compare numerically: `booking10` sorts after `booking9`.
