"""Mutant: stock is deducted inside the validation loop, so a later invalid line leaves
earlier lines half-applied."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import count


@dataclass
class Discount:
    percent: int
    start: int
    end: int


@dataclass
class Product:
    price: int
    stock: int = 0
    sold: int = 0  # net of returns
    discounts: list[Discount] = field(default_factory=list)


@dataclass
class OrderLine:
    qty: int
    unit_price: int  # fixed at the moment of sale
    returned: int = 0


class Inventory:
    def __init__(self) -> None:
        self.products: dict[str, Product] = {}
        self.orders: dict[str, dict[str, OrderLine]] = {}
        self.ledger: list[tuple[int, int]] = []  # (timestamp, +sale or -refund)
        self._order_ids = count(1)

    # -- helpers ------------------------------------------------------------------------
    def _unit_price(self, product: Product, timestamp: int) -> int:
        percent = max(
            (d.percent for d in product.discounts if d.start <= timestamp < d.end), default=0
        )
        return product.price * (100 - percent) // 100

    # -- Level 1 ------------------------------------------------------------------------
    def add_product(self, timestamp: int, sku: str, price: int) -> bool:
        """Add a product with 0 stock; return False if it already exists."""
        if sku in self.products:
            return False
        self.products[sku] = Product(price)
        return True

    def restock(self, timestamp: int, sku: str, qty: int) -> int | None:
        """Add qty units of stock and return the new level; None if missing or qty <= 0."""
        product = self.products.get(sku)
        if product is None or qty <= 0:
            return None
        product.stock += qty
        return product.stock

    def sell(self, timestamp: int, sku: str, qty: int) -> str | None:
        """Sell qty units and return an id "order1", "order2", ..., or None if the sale fails."""
        return self.place_order(timestamp, [(sku, qty)])

    # -- Level 2 ------------------------------------------------------------------------
    def place_order(self, timestamp: int, lines: list[tuple[str, int]]) -> str | None:
        """Sell all (sku, qty) lines as one order sharing sell's ids; all or nothing, else None."""
        if not lines:
            return None
        wanted: Counter[str] = Counter()
        for sku, qty in lines:
            product = self.products.get(sku)
            if product is None or qty <= 0 or product.stock < qty:
                return None
            product.stock -= qty  # BUG: deducted before later lines are validated
            product.sold += qty
            wanted[sku] += qty
        order_id = f"order{next(self._order_ids)}"
        order = {}
        for sku, qty in wanted.items():
            unit = self._unit_price(self.products[sku], timestamp)
            order[sku] = OrderLine(qty, unit)
            self.ledger.append((timestamp, unit * qty))
        self.orders[order_id] = order
        return order_id

    def top_sellers(self, timestamp: int, n: int) -> str:
        """Return up to n products with units sold > 0 as "A(4), B(2)", most sold, then sku."""
        ranked = sorted(
            ((sku, p.sold) for sku, p in self.products.items() if p.sold > 0),
            key=lambda item: (-item[1], item[0]),
        )
        return ", ".join(f"{sku}({sold})" for sku, sold in ranked[:n])

    # -- Level 3 ------------------------------------------------------------------------
    def set_price(self, timestamp: int, sku: str, price: int) -> bool:
        """Change the price for future sales only; return False for a missing product."""
        product = self.products.get(sku)
        if product is None:
            return False
        product.price = price
        return True

    def return_items(self, timestamp: int, order_id: str, sku: str, qty: int) -> int | None:
        """Put units from an order back in stock; return the refund at the unit price paid."""
        line = self.orders.get(order_id, {}).get(sku)
        if line is None or qty <= 0 or qty > line.qty - line.returned:
            return None
        line.returned += qty
        product = self.products[sku]
        product.stock += qty
        product.sold -= qty
        refund = qty * line.unit_price
        self.ledger.append((timestamp, -refund))
        return refund

    # -- Level 4 ------------------------------------------------------------------------
    def add_discount(
        self, timestamp: int, sku: str, percent: int, start_ts: int, end_ts: int
    ) -> bool:
        """Discount sales made in [start_ts, end_ts); return False for a missing product."""
        product = self.products.get(sku)
        if product is None:
            return False
        product.discounts.append(Discount(percent, start_ts, end_ts))
        return True

    def revenue(self, timestamp: int, start_ts: int, end_ts: int) -> int:
        """Return sales made in [start_ts, end_ts) minus refunds issued in that window."""
        return sum(amount for ts, amount in self.ledger if start_ts <= ts < end_ts)
