"""Mutant: guest_bookings breaks check-in ties by the id string, so booking10 sorts before booking9."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

BOOKING = "booking"
HOLD = "hold"


@dataclass
class Listing:
    price: int
    overrides: dict[int, int] = field(default_factory=dict)

    def night_price(self, night: int) -> int:
        return self.overrides.get(night, self.price)


@dataclass
class Reservation:
    """A booking or a hold. Both block nights; only the rules for when differ."""

    kind: str  # BOOKING or HOLD
    seq: int  # numeric part of the id, so ids sort numerically
    listing_id: str
    guest_id: str
    check_in: int
    check_out: int  # exclusive
    expires_at: float = math.inf  # holds only
    total: int = 0  # bookings only: the price locked in when the booking was made
    cancelled: bool = False
    confirmed: bool = False

    @property
    def id(self) -> str:
        return f"{self.kind}{self.seq}"

    def blocks(self, ts: int) -> bool:
        if self.kind == BOOKING:
            return not self.cancelled
        return not self.confirmed and ts < self.expires_at

    def overlaps(self, check_in: int, check_out: int) -> bool:
        return self.check_in < check_out and check_in < self.check_out


class BookingCalendar:
    def __init__(self) -> None:
        self.listings: dict[str, Listing] = {}
        self.reservations: dict[str, Reservation] = {}
        self.counters = {BOOKING: 0, HOLD: 0}

    # -- helpers ------------------------------------------------------------------------
    def _is_free(self, ts: int, listing_id: str, check_in: int, check_out: int) -> bool:
        return not any(
            r.listing_id == listing_id and r.blocks(ts) and r.overlaps(check_in, check_out)
            for r in self.reservations.values()
        )

    def _can_reserve(self, ts: int, listing_id: str, check_in: int, check_out: int) -> bool:
        return (
            listing_id in self.listings
            and check_in < check_out
            and self._is_free(ts, listing_id, check_in, check_out)
        )

    def _quote(self, listing_id: str, check_in: int, check_out: int) -> int:
        listing = self.listings[listing_id]
        return sum(listing.night_price(night) for night in range(check_in, check_out))

    def _create(self, kind: str, listing_id: str, guest_id: str, check_in: int, check_out: int,
                expires_at: float = math.inf) -> str:
        """The only code that issues ids: callers validate first, so failures never use one."""
        self.counters[kind] += 1
        total = self._quote(listing_id, check_in, check_out) if kind == BOOKING else 0
        r = Reservation(kind, self.counters[kind], listing_id, guest_id, check_in, check_out,
                        expires_at, total)
        self.reservations[r.id] = r
        return r.id

    def _get(self, rid: str, kind: str) -> Reservation | None:
        r = self.reservations.get(rid)
        return r if r is not None and r.kind == kind else None

    def _active_bookings(self) -> list[Reservation]:
        return [r for r in self.reservations.values() if r.kind == BOOKING and not r.cancelled]

    # -- Level 1 ------------------------------------------------------------------------
    def add_listing(self, timestamp: int, listing_id: str, nightly_price: int) -> bool:
        """Add a listing with a nightly price; return False if it already exists."""
        if listing_id in self.listings:
            return False
        self.listings[listing_id] = Listing(nightly_price)
        return True

    def book(self, timestamp: int, listing_id: str, guest_id: str, check_in: int,
             check_out: int) -> str | None:
        """Book nights check_in..check_out-1; return "bookingN", or None if invalid or taken."""
        if not self._can_reserve(timestamp, listing_id, check_in, check_out):
            return None
        return self._create(BOOKING, listing_id, guest_id, check_in, check_out)

    def cancel(self, timestamp: int, booking_id: str) -> bool:
        """Cancel a booking, freeing its nights; return False if missing or already cancelled."""
        r = self._get(booking_id, BOOKING)
        if r is None or r.cancelled:
            return False
        r.cancelled = True
        return True

    # -- Level 2 ------------------------------------------------------------------------
    def search_available(self, timestamp: int, check_in: int, check_out: int,
                         max_price: int) -> str:
        """Return free listings priced <= max_price as "A, B", sorted by price then id."""
        # Written to the Level 4 rule. With no price overrides it is identical to Level 2's.
        found = []
        for listing_id, listing in self.listings.items():
            prices = [listing.night_price(night) for night in range(check_in, check_out)]
            if all(p <= max_price for p in prices) and self._is_free(
                timestamp, listing_id, check_in, check_out
            ):
                found.append((sum(prices), listing_id))
        return ", ".join(listing_id for _, listing_id in sorted(found))

    def guest_bookings(self, timestamp: int, guest_id: str) -> str:
        """Return the guest's active bookings as "booking1(A, 3-5), ...", by check_in then id."""
        mine = [r for r in self._active_bookings() if r.guest_id == guest_id]
        mine.sort(key=lambda r: (r.check_in, r.id))
        return ", ".join(f"{r.id}({r.listing_id}, {r.check_in}-{r.check_out})" for r in mine)

    # -- Level 3 ------------------------------------------------------------------------
    def hold(self, timestamp: int, listing_id: str, guest_id: str, check_in: int,
             check_out: int, ttl: int) -> str | None:
        """Hold nights for ttl time units; return "holdN", or None on the same failures as book."""
        if not self._can_reserve(timestamp, listing_id, check_in, check_out):
            return None
        return self._create(HOLD, listing_id, guest_id, check_in, check_out, timestamp + ttl)

    def confirm_hold(self, timestamp: int, hold_id: str) -> str | None:
        """Turn an active hold into a booking and return its id, or None."""
        r = self._get(hold_id, HOLD)
        if r is None or not r.blocks(timestamp):  # missing, expired or already confirmed
            return None
        r.confirmed = True
        return self._create(BOOKING, r.listing_id, r.guest_id, r.check_in, r.check_out)

    # -- Level 4 ------------------------------------------------------------------------
    def set_night_price(self, timestamp: int, listing_id: str, night: int, price: int) -> bool:
        """Override the price of one night; return False if the listing doesn't exist."""
        listing = self.listings.get(listing_id)
        if listing is None:
            return False
        listing.overrides[night] = price
        return True

    def quote(self, timestamp: int, listing_id: str, check_in: int, check_out: int) -> int | None:
        """Return the total price of the range, or None if the listing is missing or range empty."""
        if listing_id not in self.listings or check_in >= check_out:
            return None
        return self._quote(listing_id, check_in, check_out)

    def host_revenue(self, timestamp: int, listing_id: str) -> int | None:
        """Return the sum of locked-in totals of the listing's non-cancelled bookings, or None."""
        if listing_id not in self.listings:
            return None
        return sum(r.total for r in self._active_bookings() if r.listing_id == listing_id)
