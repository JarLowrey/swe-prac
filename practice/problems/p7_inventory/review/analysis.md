The crux is that money is fixed at the moment of sale: refunds use the price actually paid, and revenue is attributed to when each sale or refund happened. Level 2's all-or-nothing orders are the other trap.

## Approach

There is one order path (`sell` is a one-line `place_order`), and it validates everything before deducting anything. Each order line records the unit price actually paid, and every sale or refund is appended to a signed ledger. Returns, price changes, discounts and revenue then all read from records made at the moment of sale.

**Data model.** `products: dict[sku, Product(price, stock, sold, discounts)]`, `orders: dict[oid, dict[sku, OrderLine(qty, unit_price, returned)]]`, and `ledger: list[(ts, ±amount)]`.

## How the crux is handled

- `place_order` first folds lines into a `Counter`, so repeated skus combine before the stock check. Then it validates every sku, quantity and stock level. Only after all checks pass does it take an order id and deduct stock, so failures change nothing and burn no ids.
- `_unit_price(p, ts)` applies the largest discount active at `ts` (`start <= ts < end`), with integer floor math. It's computed once, at sale time, and stored on the order line.
- `return_items` checks against `qty - returned` on that line and refunds at `line.unit_price`, never the current price.
- `revenue` sums ledger entries in the window. Refunds are negative entries at the return's timestamp, so attribution falls out of the data with no special logic.
- `sold` is kept net of returns, so `top_sellers` needs no separate return bookkeeping.

## Complexity

`place_order` is O(lines + discounts). `return_items` is O(1). `top_sellers` is O(P log P). `revenue` is O(ledger); a sorted ledger with prefix sums would make it O(log n) if needed.

## Common mistakes

- Deducting stock inside the validation loop, which leaves a half-applied order when a later line fails.
- Checking stock per line instead of per combined sku, so `[("A", 2), ("A", 2)]` passes with 3 in stock.
- Taking the order id before validation, so failed orders skip numbers.
- Refunding at the current price, or attributing refunds to the original sale's timestamp.
- Float discount math (`price * 0.67`), which rounds differently from integer floor.

## Key snippet

```python
def place_order(self, ts, lines):
    if not lines:
        return None
    wanted = Counter()
    for sku, qty in lines:                       # 1. validate shape
        if sku not in self.products or qty <= 0:
            return None
        wanted[sku] += qty
    if any(self.products[s].stock < q for s, q in wanted.items()):
        return None                               # 2. validate stock, combined
    oid = f"order{next(self._order_ids)}"         # 3. only now commit
    order = {}
    for sku, qty in wanted.items():
        p = self.products[sku]
        unit = self._unit_price(p, ts)
        p.stock -= qty
        p.sold += qty
        order[sku] = OrderLine(qty, unit)
        self.ledger.append((ts, unit * qty))
    self.orders[oid] = order
    return oid
```

Remember: validate the whole operation before the first write, record the price paid on the order, and keep money as a signed, timestamped ledger in integers.
