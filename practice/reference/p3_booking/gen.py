"""Random operation sequences for p3_booking `@gen` tests.

Small id spaces and a short calendar make overlaps, ties, expiries and id re-use common.
A shadow copy of the reference solution tracks which booking and hold ids really exist, so
cancel and confirm_hold mostly target live ids (plus some already-used and not-yet-issued ones).

Avoids behaviour the statement leaves open: search with an empty range, non-positive ttl,
cancelling a hold id, confirming a booking id, and ids in odd formats.
"""

from __future__ import annotations

import ast
import importlib.util
import random
import sys
from pathlib import Path

LISTINGS = ["A", "B", "C", "D"]  # "D" exists only once a random add_listing creates it
MISSING = "Z"
GUESTS = ["g1", "g2", "g3", "g4"]
PRICES = [50, 80, 100, 120]
OVERRIDES = [30, 60, 100, 150, 200]
MAX_PRICES = [60, 90, 100, 130, 200, 500]
TTLS = [1, 2, 3, 5, 8, 12, 20, 40]
FIRST_NIGHT, LAST_NIGHT = 1, 24

WEIGHTS = {
    1: {"add_listing": 1, "book": 6, "cancel": 3},
    2: {"search_available": 3, "guest_bookings": 2},
    3: {"hold": 5, "confirm_hold": 2},
    4: {"set_night_price": 3, "quote": 2, "host_revenue": 2},
}


def _reference_class():
    name = "_p3_booking_gen_reference"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name("solution.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name].BookingCalendar


def _range(rng: random.Random, allow_empty: bool) -> tuple[int, int]:
    check_in = rng.randint(FIRST_NIGHT, LAST_NIGHT)
    if allow_empty and rng.random() < 0.08:
        return check_in, check_in - rng.randint(0, 2)
    return check_in, check_in + rng.randint(1, 4)


def _listing(rng: random.Random) -> str:
    return MISSING if rng.random() < 0.05 else rng.choice(LISTINGS)


def _pick_id(rng: random.Random, prefix: str, issued: list[str]) -> str:
    """Usually a recent issued id; sometimes an older one or the next not-yet-issued one."""
    roll = rng.random()
    if not issued or roll < 0.1:
        return f"{prefix}{len(issued) + 1}"
    if roll < 0.35:
        return rng.choice(issued)
    if roll < 0.6:
        return issued[-rng.randint(1, min(3, len(issued)))]
    return issued[-1]


def _line(op: str, rng: random.Random, ts: int, bookings: list[str], holds: list[str]) -> str:
    if op == "add_listing":
        return f'add_listing({ts}, "{rng.choice(LISTINGS)}", {rng.choice(PRICES)})'
    if op == "book":
        ci, co = _range(rng, allow_empty=True)
        return f'book({ts}, "{_listing(rng)}", "{rng.choice(GUESTS)}", {ci}, {co})'
    if op == "cancel":
        return f'cancel({ts}, "{_pick_id(rng, "booking", bookings)}")'
    if op == "search_available":
        ci, co = _range(rng, allow_empty=False)
        return f"search_available({ts}, {ci}, {co}, {rng.choice(MAX_PRICES)})"
    if op == "guest_bookings":
        return f'guest_bookings({ts}, "{rng.choice(GUESTS + ["g9"])}")'
    if op == "hold":
        ci, co = _range(rng, allow_empty=True)
        guest, ttl = rng.choice(GUESTS), rng.choice(TTLS)
        return f'hold({ts}, "{_listing(rng)}", "{guest}", {ci}, {co}, {ttl})'
    if op == "confirm_hold":
        return f'confirm_hold({ts}, "{_pick_id(rng, "hold", holds)}")'
    if op == "set_night_price":
        night, price = rng.randint(FIRST_NIGHT, LAST_NIGHT + 3), rng.choice(OVERRIDES)
        return f'set_night_price({ts}, "{_listing(rng)}", {night}, {price})'
    if op == "quote":
        ci, co = _range(rng, allow_empty=True)
        return f'quote({ts}, "{_listing(rng)}", {ci}, {co})'
    return f'host_revenue({ts}, "{_listing(rng)}")'


def generate(level: int, rng: random.Random, n: int) -> list[str]:
    """Return n DSL call lines (no arrows) using only methods of levels <= level."""
    weights: dict[str, int] = {}
    for lv in range(1, level + 1):
        weights.update(WEIGHTS[lv])
    names, w = list(weights), list(weights.values())

    shadow = _reference_class()()
    bookings: list[str] = []
    holds: list[str] = []
    follow_ups: list[tuple[int, str]] = []  # (due line index, hold id): confirm soon after
    lines: list[str] = []
    ts = 0
    while len(lines) < n:
        ts += rng.choice([1, 1, 1, 2, 2, 3, 5, 8])
        if len(lines) < 3:  # start with three listings so early bookings can succeed
            line = f'add_listing({ts}, "{LISTINGS[len(lines)]}", {rng.choice(PRICES)})'
        elif follow_ups and follow_ups[0][0] <= len(lines):
            line = f'confirm_hold({ts}, "{follow_ups.pop(0)[1]}")'
        else:
            line = _line(rng.choices(names, w)[0], rng, ts, bookings, holds)
        lines.append(line)

        call, _, rest = line.partition("(")
        result = getattr(shadow, call)(*ast.literal_eval(f"({rest}"))
        if call in ("book", "confirm_hold") and result is not None:
            bookings.append(result)
        elif call == "hold" and result is not None:
            holds.append(result)
            if rng.random() < 0.6:
                follow_ups.append((len(lines) + rng.randint(0, 3), result))
    return lines
