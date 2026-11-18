class Solution:
    def shoppingOffers(self, price: list[int], special: list[list[int]], needs: list[int]) -> int:
        # Keep the offers worth trying, each as (items, cost).
        offers = []
        for offer in special:
            items, cost = tuple(offer[:-1]), offer[-1]
            # An offer with no items never changes the needs, so trying it would recurse on the
            # same state forever. An offer costing at least its items at full price can always
            # be swapped for buying those items one by one, so it never helps.
            if any(items) and cost < sum(q * p for q, p in zip(items, price, strict=True)):
                offers.append((items, cost))
        # Top-down DP, "helper + memo": the memo maps the remaining needs (a tuple, because a
        # list can't be a dict key) to the cheapest way to buy exactly those items.
        return self.cheapest(tuple(needs), price, offers, {})

    def cheapest(self, needs: tuple[int, ...], price: list[int], offers: list, memo: dict) -> int:
        """The lowest price for buying exactly `needs`."""
        if needs in memo:
            return memo[needs]  # solved already: different orders of offers lead here
        # Option 1: buy everything that's left at full price (0 when nothing is left).
        best = sum(q * p for q, p in zip(needs, price, strict=True))
        # Option 2: use one offer that fits, then buy what's left as cheaply as possible. The
        # order of offers doesn't matter, so trying each one "first" covers every plan.
        for items, cost in offers:
            left = tuple(need - q for need, q in zip(needs, items, strict=True))
            if min(left) < 0:
                continue  # the offer holds more of some item than we still need
            best = min(best, cost + self.cheapest(left, price, offers, memo))
        memo[needs] = best
        return best
