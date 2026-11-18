**Hint 1.** Without offers, the answer is `sum(price[i] * needs[i])`. Each offer is a choice:
use it once (if it fits) and solve the smaller problem that's left.

**Hint 2.** Write `cheapest(needs)`, the lowest price for buying exactly `needs`. Start from
buying everything at full price; then, for every offer that fits, try
`offer price + cheapest(needs - offer)` and keep the minimum.

**Hint 3.** Different orders of offers reach the same remaining needs (offer A then B, or B then
A). Memoize `cheapest` on the remaining needs. A list can't be a dict key, but a tuple can.

**Hint 4.** An offer fits only if it holds no more of *any* item than you still need. And watch
for an offer with no items at all: using it doesn't change the needs, so the recursion would call
itself forever. Skip it.
