"""Random call sequences for Problem 2: Banking ledger."""

from __future__ import annotations

import random

IDS = ["A", "B", "C", "D", "E"]


def generate(level: int, rng: random.Random, n: int) -> list[str]:
    """Return n DSL call lines (no arrows) using only methods of levels <= level."""
    ops = [("create", 3), ("deposit", 5), ("transfer", 6)]
    if level >= 2:
        ops.append(("top", 2))
    if level >= 3:
        ops += [("schedule", 4), ("cancel", 3)]
    if level >= 4:
        ops += [("merge", 2), ("balance", 4)]
    names = [name for name, _ in ops]
    weights = [w for _, w in ops]

    # Light bookkeeping so calls often hit live accounts and pending payments. Existence and
    # payment ownership are exact; balances are not tracked (the reference supplies results).
    live: set[str] = set()
    payments: list[dict] = []  # index i is "payment{i + 1}"

    def pick() -> str:
        if live and rng.random() < 0.8:
            return rng.choice(sorted(live))
        return rng.choice(IDS)

    lines: list[str] = []
    ts = 0
    for _ in range(n):
        ts += rng.choice([1, 1, 1, 2, 3, 5])
        op = rng.choices(names, weights)[0]
        a, b = pick(), pick()
        if op == "create":
            a = rng.choice(IDS)
            live.add(a)
            lines.append(f'create_account({ts}, "{a}")')
        elif op == "deposit":
            lines.append(f'deposit({ts}, "{a}", {rng.randint(1, 120)})')
        elif op == "transfer":
            lines.append(f'transfer({ts}, "{a}", "{b}", {rng.randint(1, 80)})')
        elif op == "top":
            lines.append(f"top_spenders({ts}, {rng.randint(1, 6)})")
        elif op == "schedule":
            delay = rng.randint(1, 25)
            if a in live:
                payments.append({"owner": a, "due": ts + delay, "cancelled": False})
            lines.append(f'schedule_payment({ts}, "{a}", {rng.randint(1, 100)}, {delay})')
        elif op == "cancel":
            pending = [i for i, p in enumerate(payments) if p["due"] > ts and not p["cancelled"]]
            if pending and rng.random() < 0.6:
                i = rng.choice(pending)
                a = payments[i]["owner"]
            else:
                i = rng.randint(0, len(payments))  # may be one past the last id
            if i in pending and payments[i]["owner"] == a:
                payments[i]["cancelled"] = True
            lines.append(f'cancel_payment({ts}, "{a}", "payment{i + 1}")')
        elif op == "merge":
            if a != b and a in live and b in live:
                live.discard(b)
                for p in payments:
                    if p["owner"] == b and p["due"] > ts:
                        p["owner"] = a
            lines.append(f'merge_accounts({ts}, "{a}", "{b}")')
        else:
            lines.append(f'get_balance({ts}, "{a}", {rng.randint(max(0, ts - 40), ts - 1)})')
    return lines
