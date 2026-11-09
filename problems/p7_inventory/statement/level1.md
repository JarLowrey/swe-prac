Build a store's stock and checkout system. Prices are integers (cents).

- `add_product(timestamp, sku, price) -> bool` adds a product with the given price. Returns `False` if the product exists. New products have 0 stock.
- `restock(timestamp, sku, qty) -> int | None` adds stock and returns the new level. Returns `None` for a missing product or `qty <= 0`.
- `sell(timestamp, sku, qty) -> str | None` sells units and returns `"order1"`, `"order2"`, ... from a global counter. Returns `None` for a missing product, `qty <= 0`, or insufficient stock. Failed sales don't use up an order id.
