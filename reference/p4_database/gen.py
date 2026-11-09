"""Random operation sequences for p4_database."""

from __future__ import annotations

import random

KEYS = ["a", "b", "c", "d"]
FIELDS = ["f", "fa", "fb", "g", "ga"]
PREFIXES = ["", "f", "fa", "g", "ga", "x"]


def _value(rng: random.Random) -> str:
    return f"v{rng.randint(1, 9)}"


def generate(level: int, rng: random.Random, n: int) -> list[str]:
    """Return n DSL call lines (no arrows) using only methods of levels <= level."""
    weights = {"set": 20, "get": 18, "delete": 10}
    if level >= 2:
        weights |= {"scan": 8, "scan_by_prefix": 8}
    if level >= 3:
        weights |= {"set": 14, "set_with_ttl": 20}
    if level >= 4:
        weights |= {"backup": 7, "restore": 6}
    ops, op_weights = list(weights), list(weights.values())

    lines: list[str] = []
    backup_times: list[int] = []
    ts = 0
    while len(lines) < n:
        ts += rng.randint(1, 4)  # gaps let TTL fields expire between calls
        op = rng.choices(ops, op_weights)[0]
        key, field = rng.choice(KEYS), rng.choice(FIELDS)
        if level >= 3:
            # The last key only ever gets TTL fields (and gets many of them), so it
            # keeps flipping between live and expired, in and out of backup counts.
            if op == "set":
                key = rng.choice(KEYS[:-1])
            elif op == "set_with_ttl" and rng.random() < 0.4:
                key = KEYS[-1]
        if op == "set":
            lines.append(f'set({ts}, "{key}", "{field}", "{_value(rng)}")')
        elif op == "get":
            lines.append(f'get({ts}, "{key}", "{field}")')
        elif op == "delete":
            lines.append(f'delete({ts}, "{key}", "{field}")')
        elif op == "scan":
            lines.append(f'scan({ts}, "{key}")')
        elif op == "scan_by_prefix":
            lines.append(f'scan_by_prefix({ts}, "{key}", "{rng.choice(PREFIXES)}")')
        elif op == "set_with_ttl":
            ttl = rng.randint(1, 30)
            lines.append(f'set_with_ttl({ts}, "{key}", "{field}", "{_value(rng)}", {ttl})')
        elif op == "backup":
            lines.append(f"backup({ts})")
            backup_times.append(ts)
        elif op == "restore":
            if not backup_times:
                continue  # a restore needs an earlier backup; draw another operation
            if rng.random() < 0.4:
                target = rng.choice(backup_times)  # exactly at a backup timestamp
            else:
                target = rng.randint(backup_times[0], ts - 1)
            lines.append(f"restore({ts}, {target})")
    return lines
