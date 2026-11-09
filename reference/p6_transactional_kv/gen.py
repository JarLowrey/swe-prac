"""Random operation sequences for p6_transactional_kv (expected values come from the reference)."""

from __future__ import annotations

import random

KEYS = ["a", "ab", "abc", "b", "ba", "c"]
VALUES = ["x", "y", "z"]
COUNT_VALUES = [*VALUES, "w"]  # "w" is never stored
PREFIXES = ["", "a", "ab", "abc", "b", "c", "d"]
MAX_DEPTH = 4


def _weights(level: int, depth: int) -> dict[str, float]:
    ops: dict[str, float] = {"set": 4, "get": 3, "delete": 3}
    if level >= 2:
        ops |= {"count": 2, "list_keys": 2}
    if level >= 3:
        ops |= {
            "begin": 2.0 if depth < MAX_DEPTH else 0.3,
            "commit": 1.5 if depth else 0.2,  # depth 0: exercises the False path
            "rollback": 1.0 if depth else 0.2,
        }
    if level >= 4:
        ops["get_at"] = 3
    return ops


def generate(level: int, rng: random.Random, n: int) -> list[str]:
    """Return n DSL call lines (no arrows) using only methods of levels <= level."""
    lines: list[str] = []
    ts = 0
    depth = 0  # open transactions, tracked only to steer the weights
    for _ in range(n):
        ts += rng.randint(1, 3)
        ops = _weights(level, depth)
        op = rng.choices(list(ops), weights=list(ops.values()))[0]
        key = rng.choice(KEYS)
        if op == "set":
            lines.append(f'set({ts}, "{key}", "{rng.choice(VALUES)}")')
        elif op in ("get", "delete"):
            lines.append(f'{op}({ts}, "{key}")')
        elif op == "count":
            lines.append(f'count({ts}, "{rng.choice(COUNT_VALUES)}")')
        elif op == "list_keys":
            lines.append(f'list_keys({ts}, "{rng.choice(PREFIXES)}")')
        elif op == "begin":
            depth += 1
            lines.append(f"begin({ts})")
        elif op in ("commit", "rollback"):
            depth = max(0, depth - 1)
            lines.append(f"{op}({ts})")
        else:  # get_at: always a past time, sometimes recent, sometimes far back
            low = max(0, ts - 12) if rng.random() < 0.6 else 0
            lines.append(f'get_at({ts}, "{key}", {rng.randint(low, ts - 1)})')
    return lines
