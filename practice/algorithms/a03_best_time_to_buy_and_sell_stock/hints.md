**Hint 1.** The brute force tries every buy day `i` and every later sell day `j`: O(n²). Note
that the answer is not simply `max(prices) - min(prices)`: in `[5, 9, 1]` the lowest price comes
after the highest.

**Hint 2.** Fix the sell day `j`. Which buy day is best for it? Only one number about the days
before `j` matters.

**Hint 3.** The best buy for day `j` is the cheapest day before it. Walk forward keeping the lowest
price seen so far; selling today earns `price - lowest`.

**Hint 4.** Keep two variables: `lowest` (start it at infinity, which also handles an empty array)
and `best` (start it at 0, the "don't trade" answer). For each price, update `lowest`, then
`best = max(best, price - lowest)`.
