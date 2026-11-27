"""Reference solution for Problem 7: Inventory and point of sale."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import count

# Design in brief
# ---------------
# - There is ONE order path: sell is place_order with a single line. Validation, id allocation
#   and bookkeeping exist once, so single and multi-line sales cannot drift apart.
# - place_order validates everything first and only then changes state. A failed order changes
#   nothing and does not consume an order id.
# - Each order line stores the unit price actually paid. Refunds and revenue read that, never
#   the product's current price, so later price changes and discounts cannot rewrite the past.
# - Money flows through a ledger of (timestamp, +sale or -refund), so revenue is a plain sum
#   over a window.


@dataclass
class Discount:
    percent: int
    start: int  # the discount applies to sales with start <= timestamp < end
    end: int


@dataclass
class Product:
    price: int  # the current price; each sale copies it (after discounts) into its order line
    stock: int = 0
    sold: int = 0  # net of returns
    discounts: list[Discount] = field(default_factory=list)


@dataclass
class OrderLine:
    qty: int
    unit_price: int  # fixed at the moment of sale
    returned: int = 0  # units already returned; qty - returned can still be returned


class Inventory:
    def __init__(self) -> None:
        self.products: dict[str, Product] = {}
        self.orders: dict[str, dict[str, OrderLine]] = {}  # order id -> {sku -> line}
        self.ledger: list[tuple[int, int]] = []  # (timestamp, +sale or -refund)
        # Shared by sell and place_order. It is only advanced after validation has passed, so a
        # failed order never uses up an id.
        self._order_ids = count(1)

    # -- helpers ------------------------------------------------------------------------
    def _unit_price(self, product: Product, timestamp: int) -> int:
        # Of the discounts active at `timestamp` only the LARGEST applies; they do not stack.
        # default=0 covers "no discount active".
        percent = max(
            (d.percent for d in product.discounts if d.start <= timestamp < d.end), default=0
        )
        # Integer maths: multiply first, then floor-divide, which rounds down as the problem
        # asks and avoids floats entirely.
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
        # The single order path: a one-line order. This is why Level 2 needs no second id counter.
        return self.place_order(timestamp, [(sku, qty)])

    # -- Level 2 ------------------------------------------------------------------------
    def place_order(self, timestamp: int, lines: list[tuple[str, int]]) -> str | None:
        """Sell all (sku, qty) lines as one order sharing sell's ids; all or nothing, else None."""
        if not lines:  # an empty order is invalid
            return None
        # A Counter merges repeated skus: [("A", 2), ("A", 3)] is one line of 5. Stock has to be
        # checked against the COMBINED quantity, not line by line.
        wanted: Counter[str] = Counter()
        for sku, qty in lines:  # 1. validate every line
            if sku not in self.products or qty <= 0:
                return None
            wanted[sku] += qty
        if any(self.products[sku].stock < qty for sku, qty in wanted.items()):
            return None  # 2. validate stock for the combined quantities
        # 3. only now commit. Nothing below can fail, so the order really is all or nothing.
        # Stock is never touched in the loops above: deducting during validation would leave a
        # half-applied order behind when a later line failed.
        order_id = f"order{next(self._order_ids)}"
        order = {}
        for sku, qty in wanted.items():
            product = self.products[sku]
            # The price is looked up once, at the order's timestamp, and stored in the line.
            unit = self._unit_price(product, timestamp)
            product.stock -= qty
            product.sold += qty
            order[sku] = OrderLine(qty, unit)
            self.ledger.append((timestamp, unit * qty))  # one ledger entry per sku
        self.orders[order_id] = order
        return order_id

    def top_sellers(self, timestamp: int, n: int) -> str:
        """Return up to n products with units sold > 0 as "A(4), B(2)", most sold, then sku."""
        # `sold` is already net of returns (return_items reduces it), so returned units drop out
        # of the ranking by themselves. Products at 0 are left out. Most sold first, then sku.
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
        # Only the product changes. Existing order lines keep the unit price they were sold at.
        product.price = price
        return True

    def return_items(self, timestamp: int, order_id: str, sku: str, qty: int) -> int | None:
        """Put units from an order back in stock; return the refund at the unit price paid."""
        # The chained .get covers both an unknown order and a sku that is not in that order.
        line = self.orders.get(order_id, {}).get(sku)
        # Compare with the units NOT YET returned, so partial and repeated returns work while
        # returning more than was sold, or the same units twice, fails.
        if line is None or qty <= 0 or qty > line.qty - line.returned:
            return None
        line.returned += qty
        product = self.products[sku]
        product.stock += qty  # back on the shelf
        product.sold -= qty  # and no longer counted as sold
        # Refund at the price paid in this order, never today's price.
        refund = qty * line.unit_price
        # A negative entry: revenue nets refunds in the window they were ISSUED, not the window
        # of the original sale.
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
        # Just record it. The discount is applied by _unit_price at sale time, so sales made
        # before or after the window, and sales already made, are not affected.
        product.discounts.append(Discount(percent, start_ts, end_ts))
        return True

    def revenue(self, timestamp: int, start_ts: int, end_ts: int) -> int:
        """Return sales made in [start_ts, end_ts) minus refunds issued in that window."""
        # Sales are positive entries and refunds negative ones, each with its own timestamp,
        # so one windowed sum gives the net. The window is half-open, like every other range.
        return sum(amount for ts, amount in self.ledger if start_ts <= ts < end_ts)
