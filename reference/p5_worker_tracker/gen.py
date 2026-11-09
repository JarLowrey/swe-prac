"""Random call sequences for p5_worker_tracker (expected values come from the reference)."""

from __future__ import annotations

import random

WORKERS = ["a", "b", "c", "d", "e"]
MISSING = "zz"  # never added
POSITIONS = ["dev", "pm", "qa"]
UNUSED_POSITION = "ops"  # never held by anyone


def _worker(rng: random.Random) -> str:
    return MISSING if rng.random() < 0.05 else rng.choice(WORKERS)


def generate(level: int, rng: random.Random, n: int) -> list[str]:
    """Return n DSL call lines (no arrows) using only methods of levels <= level."""
    ops = ["add"] + ["register"] * 6 + ["get"] * 2
    if level >= 2:
        ops += ["top"] * 3
    if level >= 3:
        ops += ["promote"] * 3 + ["salary"] * 3
    if level >= 4:
        ops += ["double"] * 2 + ["salary"] * 2

    # four workers exist from the start; the fifth only appears through a later random add
    first_adds = rng.sample(WORKERS, 4)
    lines: list[str] = []
    ts = 0
    for i in range(n):
        ts += rng.randint(1, 6)
        op = "add" if i < len(first_adds) else rng.choice(ops)
        if op == "add":
            position = rng.choice(POSITIONS)
            worker_id = first_adds[i] if i < len(first_adds) else rng.choice(WORKERS)
            lines.append(f'add_worker({ts}, "{worker_id}", "{position}", {rng.randint(1, 20)})')
        elif op == "register":
            lines.append(f'register({ts}, "{_worker(rng)}")')
        elif op == "get":
            lines.append(f'get({ts}, "{_worker(rng)}")')
        elif op == "top":
            position = rng.choice([*POSITIONS, UNUSED_POSITION])
            lines.append(f'top_n_workers({ts}, {rng.randint(1, 6)}, "{position}")')
        elif op == "promote":
            # start_timestamp is never in the past, so "first entry at or after" is unambiguous
            start = ts + rng.randint(0, 30)
            position = rng.choice(POSITIONS)
            lines.append(
                f'promote({ts}, "{_worker(rng)}", "{position}", {rng.randint(1, 20)}, {start})'
            )
        elif op == "salary":
            if rng.random() < 0.25:  # the whole history so far
                lo, hi = 0, ts + 1
            else:
                lo = rng.randint(0, ts)
                hi = lo + rng.randint(1, 150)
            lines.append(f'calc_salary({ts}, "{_worker(rng)}", {lo}, {hi})')
        else:  # double
            lo = rng.randint(0, ts + 40)
            hi = lo + rng.randint(1, 30)
            lines.append(f"set_double_time({ts}, {lo}, {hi})")
    return lines
