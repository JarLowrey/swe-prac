- `set_price(timestamp, sku, price) -> bool` changes the price for future sales only. Returns `False` for a missing product.
- `return_items(timestamp, order_id, sku, qty) -> int | None` returns units from an order, puts them back in stock, and returns the refund: `qty` times the unit price paid in that order. Returns `None` if the order doesn't exist, the sku isn't in it, `qty <= 0`, or `qty` exceeds the units of that sku not yet returned from that order.

Changed behaviour: returned units no longer count toward `top_sellers`.
