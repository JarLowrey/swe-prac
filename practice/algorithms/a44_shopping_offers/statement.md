A shop sells `n` kinds of items. One item of kind `i` costs `price[i]`, and you want to buy exactly
`needs[i]` items of kind `i`.

The shop also has special offers. Each offer `special[j]` is a list of `n + 1` numbers: the first
`n` say how many items of each kind the offer contains, and the last is the price of the whole
offer. You can use an offer as many times as you like.

Return the lowest price for buying exactly `needs`. You may not buy more items than you need,
even if that would be cheaper.

**Example 1**

```
Input:  price = [2, 5], special = [[3, 0, 5], [1, 2, 10]], needs = [3, 2]
Output: 14
```

Item 0 costs 2 and item 1 costs 5. Offer 0 is three of item 0 for 5; offer 1 is one of item 0
and two of item 1 for 10.

| Plan | Cost |
|---|---|
| everything at full price: 3 × 2 + 2 × 5 | 16 |
| offer 0, then two of item 1 at full price | 5 + 10 = 15 |
| offer 1, then two of item 0 at full price | 10 + 4 = **14** |
| offer 0 and offer 1 | not allowed: four of item 0 |

**Example 2**

```
Input:  price = [2, 3, 4], special = [[1, 1, 0, 4], [2, 2, 1, 9]], needs = [1, 2, 1]
Output: 11
```

Offer 1 contains two of item 0 but you need only one, so it can't be used. Offer 0 once (4), then
one of item 1 (3) and one of item 2 (4): 11.

**Example 3**

```
Input:  price = [2, 2], special = [[2, 2, 0]], needs = [1, 1]
Output: 4
```

The offer is free, but it contains more than you need, so you buy the two items one at a time.

**Constraints**

- `n == len(price) == len(needs)`, and `1 <= n <= 6`
- `0 <= price[i], needs[i] <= 10`
- `0 <= len(special) <= 100`, and every `len(special[j]) == n + 1`
- `0 <= special[j][i] <= 50`: any quantity can be 0, and so can an offer's price
