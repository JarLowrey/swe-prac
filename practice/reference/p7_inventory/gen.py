"""Random operation sequences for Problem 7 (inventory and point of sale)."""

from __future__ import annotations

import random

SKUS = ["A", "B", "C", "D", "E"]
PRICES = [97, 99, 100, 150, 199, 250, 333]
PERCENTS = [5, 10, 25, 32, 33, 34, 50, 90]


class _Shadow:
    """Just enough state to aim returns at real orders; expected values come from the reference."""

    def __init__(self) -> None:
        self.stock: dict[str, int] = {}
        self.orders: list[dict[str, int]] = []  # per order: units not yet returned, per sku

    def order(self, lines: list[tuple[str, int]]) -> None:
        wanted: dict[str, int] = {}
        for sku, qty in lines:
            if sku not in self.stock or qty <= 0:
                return
            wanted[sku] = wanted.get(sku, 0) + qty
        if not wanted or any(self.stock[s] < q for s, q in wanted.items()):
            return
        for sku, qty in wanted.items():
            self.stock[sku] -= qty
        self.orders.append(wanted)

    def give_back(self, index: int, sku: str, qty: int) -> None:
        if 0 <= index < len(self.orders):
            left = self.orders[index].get(sku, 0)
            if 0 < qty <= left:
                self.orders[index][sku] = left - qty
                self.stock[sku] += qty


def _qty(rng: random.Random) -> int:
    return rng.choice([0, -1]) if rng.random() < 0.1 else rng.choice([1, 1, 1, 2, 2, 3, 4])


def generate(level: int, rng: random.Random, n: int) -> list[str]:
    """Return n DSL call lines (no arrows) using only methods of levels <= level."""
    weights = {"add_product": 1, "restock": 4, "sell": 4}
    if level >= 2:
        weights |= {"place_order": 4, "top_sellers": 2}
    if level >= 3:
        weights |= {"set_price": 1, "return_items": 4}
    if level >= 4:
        weights |= {"add_discount": 3, "revenue": 3}
    ops, op_weights = list(weights), list(weights.values())

    shadow = _Shadow()
    out: list[str] = []
    ts = 0
    for _ in range(n):
        ts += rng.randint(1, 3)
        op = "add_product" if len(shadow.stock) < 2 else rng.choices(ops, op_weights)[0]
        sku = rng.choice(SKUS)
        if op == "add_product":
            out.append(f'add_product({ts}, "{sku}", {rng.choice(PRICES)})')
            shadow.stock.setdefault(sku, 0)
        elif op == "restock":
            qty = rng.choice([-2, 0, 1, 3, 5, 8, 10])
            out.append(f'restock({ts}, "{sku}", {qty})')
            if sku in shadow.stock and qty > 0:
                shadow.stock[sku] += qty
        elif op == "sell":
            qty = _qty(rng)
            out.append(f'sell({ts}, "{sku}", {qty})')
            shadow.order([(sku, qty)])
        elif op == "place_order":
            lines = [(rng.choice(SKUS), _qty(rng)) for _ in range(rng.choice([0, 1, 2, 2, 3]))]
            out.append(f"place_order({ts}, {lines!r})")
            shadow.order(lines)
        elif op == "top_sellers":
            out.append(f"top_sellers({ts}, {rng.randint(1, 6)})")
        elif op == "set_price":
            out.append(f'set_price({ts}, "{sku}", {rng.choice(PRICES)})')
        elif op == "return_items":
            returnable = [
                (i, s) for i, order in enumerate(shadow.orders) for s, left in order.items() if left
            ]
            if returnable and rng.random() < 0.8:
                index, sku = rng.choice(returnable)
                left = shadow.orders[index][sku]
                qty = rng.choice([1, 1, left, left, left + 1, 0])
            else:
                index = rng.randint(-1, len(shadow.orders) + 1)
                qty = rng.choice([1, 2])
            out.append(f'return_items({ts}, "order{index + 1}", "{sku}", {qty})')
            shadow.give_back(index, sku, qty)
        elif op == "add_discount":
            start = ts + rng.randint(0, 5)  # never covers a sale that already happened
            end = start + rng.choice([rng.randint(2, 12), rng.randint(20, 150)])
            out.append(f'add_discount({ts}, "{sku}", {rng.choice(PERCENTS)}, {start}, {end})')
        elif op == "revenue":
            start = rng.randint(max(0, ts - 40), ts)
            end = rng.randint(start + 1, min(ts + 2, start + 25))
            out.append(f"revenue({ts}, {start}, {end})")
    return out
